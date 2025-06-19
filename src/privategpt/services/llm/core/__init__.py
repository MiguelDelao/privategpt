from __future__ import annotations

from typing import Protocol, AsyncIterator, Dict, Any, List


class LLMPort(Protocol):
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a single response to a prompt."""
        ...
    
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Generate a streaming response to a prompt."""
        ...
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response for a conversation."""
        ...
        
    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """Generate streaming response for a conversation."""
        ...
    
    async def get_models(self) -> List[Dict[str, Any]]:
        """Get available models."""
        ...
    
    async def health_check(self) -> bool:
        """Check if the LLM service is healthy."""
        ... 