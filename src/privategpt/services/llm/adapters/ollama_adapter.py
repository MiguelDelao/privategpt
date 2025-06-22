from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Dict, Any, List, Optional

import httpx
from datetime import datetime
from privategpt.services.llm.core import LLMPort, ModelInfo, ChatResponse
from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)


class OllamaAdapter(LLMPort):
    """Ollama adapter for LLM operations."""
    
    def __init__(
        self,
        base_url: str,
        default_model: Optional[str] = None,
        timeout: float = 600.0,
        enabled: bool = True
    ):
        self.base_url = base_url
        self.default_model = default_model or settings.llm_default_model
        self.timeout = timeout
        self.enabled = enabled
        self.client = httpx.AsyncClient(timeout=timeout)
        
            
    async def chat(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> ChatResponse:
        """Generate response for a conversation using specified model."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model_name,
                    "messages": messages,
                    "stream": False,
                    "options": self._build_options(**kwargs)
                }
            )
            response.raise_for_status()
            result = response.json()
            
            content = result.get("message", {}).get("content", "")
            input_tokens = result.get("prompt_eval_count", 0)
            output_tokens = result.get("eval_count", 0)
            total_tokens = input_tokens + output_tokens
            
            return ChatResponse(
                content=content,
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens
            )
            
        except httpx.HTTPError as e:
            logger.error(f"Ollama chat error: {e}")
            raise RuntimeError(f"Failed to generate chat response: {e}")
            
    async def chat_stream(self, model_name: str, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """Generate streaming response for a conversation using specified model."""
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": model_name,
                    "messages": messages,
                    "stream": True,
                    "options": self._build_options(**kwargs)
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            message = data.get("message", {})
                            if "content" in message:
                                yield message["content"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.HTTPError as e:
            logger.error(f"Ollama chat stream error: {e}")
            raise RuntimeError(f"Failed to stream chat response: {e}")
            
    async def get_available_models(self) -> List[ModelInfo]:
        """Get list of models available from this Ollama instance."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            result = response.json()
            
            models = []
            for model_data in result.get("models", []):
                model_info = ModelInfo(
                    name=model_data.get("name", ""),
                    provider="ollama",
                    type="local",
                    available=True,
                    description=f"Ollama model: {model_data.get('name', '')}",
                    parameter_size=self._extract_parameter_size(model_data.get("name", "")),
                    capabilities=["chat", "completion", "streaming"],
                    cost_per_token=0.0,  # Local models are free
                    last_checked=datetime.utcnow()
                )
                models.append(model_info)
            
            return models
            
        except httpx.HTTPError as e:
            logger.error(f"Ollama models error: {e}")
            return []
            
    async def is_enabled(self) -> bool:
        """Check if this provider is currently enabled."""
        return self.enabled
    
    async def health_check(self) -> bool:
        """Check if the Ollama service is healthy and responsive."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        return "ollama"
    
    def get_provider_type(self) -> str:
        """Get the type of this provider."""
        return "local"
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable this provider."""
        self.enabled = enabled
        logger.info(f"Ollama provider {'enabled' if enabled else 'disabled'}")
    
    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for this provider's tokenization (estimation only)."""
        # Ollama doesn't have a tokenization API, so we use a simple estimation
        # Roughly 4 characters per token for most models
        return len(text) // 4 + 1
    
    async def get_context_limit(self, model_name: str) -> int:
        """Get context limit for a specific model."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/show",
                json={"name": model_name}
            )
            if response.status_code == 200:
                data = response.json()
                context_length = data.get("details", {}).get("context_length")
                if context_length:
                    return context_length
        except Exception as e:
            logger.warning(f"Failed to get context limit for {model_name}: {e}")
        
        # Fallback to conservative default
        return 4096
            
    def _extract_parameter_size(self, model_name: str) -> Optional[str]:
        """Extract parameter size from model name (e.g., 'llama3.2:7b' -> '7B')."""
        if ":" in model_name:
            size_part = model_name.split(":")[-1]
            if size_part.endswith("b"):
                return size_part.upper()
        return None
    
    def _build_options(self, **kwargs) -> Dict[str, Any]:
        """Build Ollama options from kwargs."""
        options = {}
        
        # Map common parameters to Ollama options
        if "temperature" in kwargs:
            options["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            options["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            options["top_k"] = kwargs["top_k"]
        if "max_tokens" in kwargs:
            options["num_predict"] = kwargs["max_tokens"]
        if "stop" in kwargs:
            options["stop"] = kwargs["stop"]
            
        return options
        
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()