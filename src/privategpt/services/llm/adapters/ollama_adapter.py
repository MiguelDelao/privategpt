from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Dict, Any, List, Optional

import httpx
from privategpt.services.llm.core import LLMPort
from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)


class OllamaAdapter(LLMPort):
    """Ollama adapter for LLM operations."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0
    ):
        self.base_url = base_url or settings.ollama_url
        self.model = model or settings.ollama_model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a single response to a prompt."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": kwargs.get("model", self.model),
                    "prompt": prompt,
                    "stream": False,
                    "options": self._build_options(**kwargs)
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
            
        except httpx.HTTPError as e:
            logger.error(f"Ollama generate error: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")
            
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Generate a streaming response to a prompt."""
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": kwargs.get("model", self.model),
                    "prompt": prompt,
                    "stream": True,
                    "options": self._build_options(**kwargs)
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.HTTPError as e:
            logger.error(f"Ollama stream error: {e}")
            raise RuntimeError(f"Failed to stream response: {e}")
            
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response for a conversation."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": messages,
                    "stream": False,
                    "options": self._build_options(**kwargs)
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
            
        except httpx.HTTPError as e:
            logger.error(f"Ollama chat error: {e}")
            raise RuntimeError(f"Failed to generate chat response: {e}")
            
    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """Generate streaming response for a conversation."""
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": kwargs.get("model", self.model),
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
            
    async def get_models(self) -> List[Dict[str, Any]]:
        """Get available models."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            result = response.json()
            return result.get("models", [])
            
        except httpx.HTTPError as e:
            logger.error(f"Ollama models error: {e}")
            return []
            
    async def health_check(self) -> bool:
        """Check if the LLM service is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False
            
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