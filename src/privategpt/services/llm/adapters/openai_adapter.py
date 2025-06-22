from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Dict, Any, List, Optional

import httpx
from datetime import datetime
from privategpt.services.llm.core import LLMPort, ModelInfo, ChatResponse

logger = logging.getLogger(__name__)


class OpenAIAdapter(LLMPort):
    """OpenAI adapter for LLM operations."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        default_model: Optional[str] = None,
        timeout: float = 30.0,
        enabled: bool = True
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model or "gpt-4"
        self.timeout = timeout
        self.enabled = enabled
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        
    async def chat(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> ChatResponse:
        """Generate response for a conversation using specified model."""
        try:
            payload = {
                "model": model_name,
                "messages": messages,
                **self._build_options(**kwargs)
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            choices = result.get("choices", [])
            if not choices:
                content = ""
            else:
                content = choices[0].get("message", {}).get("content", "")
            
            # Extract token usage
            usage = result.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
            
            return ChatResponse(
                content=content,
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens
            )
            
        except httpx.HTTPError as e:
            logger.error(f"OpenAI chat error: {e}")
            raise RuntimeError(f"Failed to generate chat response: {e}")
            
    async def chat_stream(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """Generate streaming response for a conversation using specified model."""
        try:
            payload = {
                "model": model_name,
                "messages": messages,
                "stream": True,
                **self._build_options(**kwargs)
            }
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
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
                                choices = chunk.get("choices", [])
                                if choices and "delta" in choices[0]:
                                    delta = choices[0]["delta"]
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                continue
                            
        except httpx.HTTPError as e:
            logger.error(f"OpenAI chat stream error: {e}")
            raise RuntimeError(f"Failed to stream chat response: {e}")
            
    async def get_available_models(self) -> List[ModelInfo]:
        """Get list of models available from OpenAI."""
        try:
            response = await self.client.get(f"{self.base_url}/models")
            response.raise_for_status()
            result = response.json()
            
            models = []
            for model_data in result.get("data", []):
                model_id = model_data.get("id", "")
                
                # Filter to only chat completion models
                if not any(x in model_id.lower() for x in ["gpt", "o1"]):
                    continue
                
                model_info = ModelInfo(
                    name=model_id,
                    provider="openai",
                    type="api",
                    available=True,
                    description=f"OpenAI model: {model_id}",
                    parameter_size=self._extract_parameter_size(model_id),
                    capabilities=["chat", "completion", "streaming"],
                    cost_per_token=self._get_model_cost(model_id),
                    last_checked=datetime.utcnow()
                )
                models.append(model_info)
            
            return models
            
        except httpx.HTTPError as e:
            logger.error(f"OpenAI models error: {e}")
            return []
            
    async def is_enabled(self) -> bool:
        """Check if this provider is currently enabled."""
        return self.enabled
    
    async def health_check(self) -> bool:
        """Check if the OpenAI API is healthy and responsive."""
        try:
            response = await self.client.get(f"{self.base_url}/models")
            return response.status_code == 200
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        return "openai"
    
    def get_provider_type(self) -> str:
        """Get the type of this provider."""
        return "api"
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable this provider."""
        self.enabled = enabled
        logger.info(f"OpenAI provider {'enabled' if enabled else 'disabled'}")
    
    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for this provider's tokenization."""
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(model_name)
            return len(encoding.encode(text))
        except Exception:
            # Fallback estimation if tiktoken not available
            return len(text) // 4 + 1
    
    async def get_context_limit(self, model_name: str) -> int:
        """Get context limit for a specific model."""
        # Known OpenAI model context limits
        context_limits = {
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4-turbo-preview": 128000,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
            "o1-preview": 128000,
            "o1-mini": 128000
        }
        
        # Find exact match or partial match
        for model_prefix, limit in context_limits.items():
            if model_name.startswith(model_prefix):
                return limit
        
        # Default fallback
        return 4096
            
    def _extract_parameter_size(self, model_name: str) -> Optional[str]:
        """Extract parameter size from model name."""
        # Simple mapping for known OpenAI models
        size_map = {
            "gpt-4": "175B",
            "gpt-4-turbo": "175B", 
            "gpt-3.5-turbo": "175B",
            "o1-preview": "Unknown",
            "o1-mini": "Unknown"
        }
        
        for model_prefix, size in size_map.items():
            if model_name.startswith(model_prefix):
                return size
        
        return None
    
    def _get_model_cost(self, model_name: str) -> Optional[float]:
        """Get cost per token for model (approximate)."""
        # Rough cost estimates per 1K tokens (input tokens)
        cost_map = {
            "gpt-4": 0.03,
            "gpt-4-turbo": 0.01,
            "gpt-3.5-turbo": 0.0015,
            "o1-preview": 0.015,
            "o1-mini": 0.003
        }
        
        for model_prefix, cost in cost_map.items():
            if model_name.startswith(model_prefix):
                return cost / 1000  # Convert to per-token cost
        
        return None
    
    def _build_options(self, **kwargs) -> Dict[str, Any]:
        """Build OpenAI API options from kwargs."""
        options = {}
        
        # Map common parameters to OpenAI API parameters
        if "temperature" in kwargs:
            options["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            options["top_p"] = kwargs["top_p"]
        if "max_tokens" in kwargs:
            options["max_tokens"] = kwargs["max_tokens"]
        if "stop" in kwargs:
            options["stop"] = kwargs["stop"]
        if "frequency_penalty" in kwargs:
            options["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            options["presence_penalty"] = kwargs["presence_penalty"]
            
        return options
        
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()