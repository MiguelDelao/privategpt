from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Dict, Any, List, Optional

import httpx
from datetime import datetime
from privategpt.services.llm.core import LLMPort, ModelInfo, ChatResponse

logger = logging.getLogger(__name__)


class AnthropicAdapter(LLMPort):
    """Anthropic (Claude) adapter for LLM operations."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        default_model: Optional[str] = None,
        timeout: float = 30.0,
        enabled: bool = True,
        available_models: Optional[List[str]] = None
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model or "claude-3-5-sonnet-20241022"
        self.timeout = timeout
        self.enabled = enabled
        self.available_models = available_models or []
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
        )
        
    async def chat(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> ChatResponse:
        """Generate response for a conversation using specified model."""
        try:
            # Map model names to actual Anthropic model IDs
            model_mapping = {
                "claude-3-7-sonnet-latest": "claude-3-5-sonnet-20241022"
            }
            actual_model = model_mapping.get(model_name, model_name)
            
            # Convert messages to Anthropic format
            anthropic_messages = self._convert_messages(messages)
            system_message = self._extract_system_message(messages)
            
            payload = {
                "model": actual_model,
                "messages": anthropic_messages,
                "max_tokens": kwargs.get("max_tokens", 1024),
                **self._build_options(**kwargs)
            }
            
            if system_message:
                payload["system"] = system_message
            
            logger.info(f"Sending to Anthropic API: {json.dumps(payload, indent=2)}")
            
            response = await self.client.post(
                f"{self.base_url}/v1/messages",
                json=payload
            )
            if response.status_code != 200:
                logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
                try:
                    error_data = response.json()
                    logger.error(f"Error details: {json.dumps(error_data, indent=2)}")
                except:
                    pass
            response.raise_for_status()
            result = response.json()
            
            # Extract content and tool calls
            content = ""
            tool_calls = []
            content_blocks = result.get("content", [])
            
            for block in content_blocks:
                if block.get("type") == "text":
                    content += block.get("text", "")
                elif block.get("type") == "tool_use":
                    # Convert tool call back to original name (undo sanitization)
                    tool_name = block.get("name", "").replace("_", ".")
                    tool_calls.append({
                        "id": block.get("id"),
                        "type": "tool_use",
                        "name": tool_name,
                        "input": block.get("input", {})
                    })
            
            # If we have tool calls, return them in the content as JSON
            if tool_calls:
                # For now, return tool calls as JSON in content
                # This is a temporary solution - ideally ChatResponse should support tool_calls
                content = json.dumps({
                    "text": content,
                    "tool_calls": tool_calls
                })
            
            # Extract token usage
            usage = result.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            total_tokens = input_tokens + output_tokens
            
            return ChatResponse(
                content=content,
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens
            )
            
        except httpx.HTTPError as e:
            logger.error(f"Anthropic chat error: {e}")
            raise RuntimeError(f"Failed to generate chat response: {e}")
            
    async def chat_stream(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """Generate streaming response for a conversation using specified model."""
        try:
            # Map model names to actual Anthropic model IDs
            model_mapping = {
                "claude-3-7-sonnet-latest": "claude-3-5-sonnet-20241022"
            }
            actual_model = model_mapping.get(model_name, model_name)
            
            # Convert messages to Anthropic format
            anthropic_messages = self._convert_messages(messages)
            system_message = self._extract_system_message(messages)
            
            payload = {
                "model": actual_model,
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
                                    elif delta.get("type") == "input_json_delta":
                                        # Tool use delta - for now just skip
                                        pass
                                elif chunk.get("type") == "content_block_start":
                                    content_block = chunk.get("content_block", {})
                                    if content_block.get("type") == "tool_use":
                                        # Tool use started - convert name back
                                        tool_name = content_block.get("name", "").replace("_", ".")
                                        yield f"\n[TOOL_USE: {tool_name}]\n"
                                elif chunk.get("type") == "content_block_stop":
                                    # Tool use or text block ended
                                    pass
                                elif chunk.get("type") == "message_delta":
                                    # Message metadata update
                                    pass
                            except json.JSONDecodeError:
                                continue
                            
        except httpx.HTTPError as e:
            logger.error(f"Anthropic chat stream error: {e}")
            raise RuntimeError(f"Failed to stream chat response: {e}")
            
    async def get_available_models(self) -> List[ModelInfo]:
        """Get list of models available from Anthropic based on configuration."""
        # If no models configured, return empty list
        if not self.available_models:
            return []
        
        # Model metadata for cost and descriptions
        model_metadata = {
            "claude-3-5-sonnet-20241022": {
                "description": "Latest Claude 3.5 Sonnet model",
                "cost_per_token": 0.003
            },
            "claude-3-5-haiku-20241022": {
                "description": "Fast and efficient Claude 3.5 Haiku model",
                "cost_per_token": 0.00025
            },
            "claude-3-opus-20240229": {
                "description": "Most capable Claude 3 Opus model",
                "cost_per_token": 0.015
            },
            "claude-3-sonnet-20240229": {
                "description": "Balanced Claude 3 Sonnet model",
                "cost_per_token": 0.003
            },
            "claude-3-haiku-20240307": {
                "description": "Fast Claude 3 Haiku model",
                "cost_per_token": 0.00025
            },
            "claude-3-7-sonnet-latest": {
                "description": "Anthropic model: claude-3-7-sonnet-latest",
                "cost_per_token": 0.003
            }
        }
        
        models = []
        for model_name in self.available_models:
            metadata = model_metadata.get(model_name, {
                "description": f"Anthropic model: {model_name}",
                "cost_per_token": 0.003  # Default cost
            })
            
            model_info = ModelInfo(
                name=model_name,
                provider="anthropic",
                type="api",
                available=True,
                description=metadata["description"],
                parameter_size="Unknown",
                capabilities=["chat", "completion", "streaming"],
                cost_per_token=metadata["cost_per_token"] / 1000,  # Convert to per-token
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
        if "tools" in kwargs:
            # Pass tools through for function calling
            options["tools"] = kwargs["tools"]
            
        return options
        
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()