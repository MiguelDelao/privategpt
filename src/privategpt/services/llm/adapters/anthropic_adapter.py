from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Dict, Any, List, Optional

import httpx
from datetime import datetime
from privategpt.services.llm.core import LLMPort, ModelInfo

logger = logging.getLogger(__name__)


class AnthropicAdapter(LLMPort):
    """Anthropic (Claude) adapter for LLM operations."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        default_model: Optional[str] = None,
        timeout: float = 30.0,
        enabled: bool = True
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model or "claude-3-5-sonnet-20241022"
        self.timeout = timeout
        self.enabled = enabled
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
        )
        
    async def chat(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response for a conversation using specified model."""
        try:
            # Convert messages to Anthropic format
            anthropic_messages = self._convert_messages(messages)
            system_message = self._extract_system_message(messages)
            
            payload = {
                "model": model_name,
                "messages": anthropic_messages,
                "max_tokens": kwargs.get("max_tokens", 1024),
                **self._build_options(**kwargs)
            }
            
            if system_message:
                payload["system"] = system_message
            
            response = await self.client.post(
                f"{self.base_url}/v1/messages",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            content = result.get("content", [])
            if content and isinstance(content, list) and len(content) > 0:
                return content[0].get("text", "")
            
            return ""
            
        except httpx.HTTPError as e:
            logger.error(f"Anthropic chat error: {e}")
            raise RuntimeError(f"Failed to generate chat response: {e}")
            
    async def chat_stream(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """Generate streaming response for a conversation using specified model."""
        try:
            # Convert messages to Anthropic format
            anthropic_messages = self._convert_messages(messages)
            system_message = self._extract_system_message(messages)
            
            payload = {
                "model": model_name,
                "messages": anthropic_messages,
                "max_tokens": kwargs.get("max_tokens", 1024),
                "stream": True,
                **self._build_options(**kwargs)
            }
            
            if system_message:
                payload["system"] = system_message
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/v1/messages",
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data.strip() == "[DONE]":
                            break
                        if data.strip():
                            try:
                                chunk = json.loads(data)
                                if chunk.get("type") == "content_block_delta":
                                    delta = chunk.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        yield delta.get("text", "")
                            except json.JSONDecodeError:
                                continue
                            
        except httpx.HTTPError as e:
            logger.error(f"Anthropic chat stream error: {e}")
            raise RuntimeError(f"Failed to stream chat response: {e}")
            
    async def get_available_models(self) -> List[ModelInfo]:
        """Get list of models available from Anthropic."""
        # Anthropic doesn't have a public models endpoint, so we return known models
        known_models = [
            {
                "name": "claude-3-5-sonnet-20241022",
                "parameter_size": "Unknown",
                "cost_per_token": 0.003,
                "description": "Latest Claude 3.5 Sonnet model"
            },
            {
                "name": "claude-3-5-haiku-20241022",
                "parameter_size": "Unknown", 
                "cost_per_token": 0.00025,
                "description": "Fast and efficient Claude 3.5 Haiku model"
            },
            {
                "name": "claude-3-opus-20240229",
                "parameter_size": "Unknown",
                "cost_per_token": 0.015,
                "description": "Most capable Claude 3 Opus model"
            },
            {
                "name": "claude-3-sonnet-20240229",
                "parameter_size": "Unknown",
                "cost_per_token": 0.003,
                "description": "Balanced Claude 3 Sonnet model"
            },
            {
                "name": "claude-3-haiku-20240307",
                "parameter_size": "Unknown",
                "cost_per_token": 0.00025,
                "description": "Fast Claude 3 Haiku model"
            }
        ]
        
        models = []
        for model_data in known_models:
            model_info = ModelInfo(
                name=model_data["name"],
                provider="anthropic",
                type="api",
                available=True,
                description=model_data["description"],
                parameter_size=model_data["parameter_size"],
                capabilities=["chat", "completion", "streaming"],
                cost_per_token=model_data["cost_per_token"] / 1000,  # Convert to per-token
                last_checked=datetime.utcnow()
            )
            models.append(model_info)
        
        return models
            
    async def is_enabled(self) -> bool:
        """Check if this provider is currently enabled."""
        return self.enabled
    
    async def health_check(self) -> bool:
        """Check if the Anthropic API is healthy and responsive."""
        try:
            # Simple test request
            payload = {
                "model": self.default_model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1
            }
            response = await self.client.post(
                f"{self.base_url}/v1/messages",
                json=payload
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        return "anthropic"
    
    def get_provider_type(self) -> str:
        """Get the type of this provider."""
        return "api"
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable this provider."""
        self.enabled = enabled
        logger.info(f"Anthropic provider {'enabled' if enabled else 'disabled'}")
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Convert messages to Anthropic format (excluding system messages)."""
        anthropic_messages = []
        for msg in messages:
            if msg.get("role") != "system":
                anthropic_messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content")
                })
        return anthropic_messages
    
    def _extract_system_message(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Extract system message content."""
        for msg in messages:
            if msg.get("role") == "system":
                return msg.get("content")
        return None
            
    def _build_options(self, **kwargs) -> Dict[str, Any]:
        """Build Anthropic API options from kwargs."""
        options = {}
        
        # Map common parameters to Anthropic API parameters
        if "temperature" in kwargs:
            options["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            options["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            options["top_k"] = kwargs["top_k"]
        if "stop" in kwargs:
            # Anthropic uses "stop_sequences" instead of "stop"
            stop_sequences = kwargs["stop"]
            if isinstance(stop_sequences, str):
                stop_sequences = [stop_sequences]
            options["stop_sequences"] = stop_sequences
            
        return options
        
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()