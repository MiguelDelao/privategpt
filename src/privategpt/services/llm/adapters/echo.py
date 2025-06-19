from __future__ import annotations

from typing import AsyncIterator, Dict, Any, List
from privategpt.services.llm.core import LLMPort


class EchoAdapter(LLMPort):
    async def generate(self, prompt: str, **kwargs) -> str:
        return f"Echo: {prompt}"
    
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        response = f"Echo: {prompt}"
        for word in response.split():
            yield word + " "
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        last_message = messages[-1] if messages else {"content": ""}
        return f"Echo: {last_message.get('content', '')}"
        
    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        last_message = messages[-1] if messages else {"content": ""}
        response = f"Echo: {last_message.get('content', '')}"
        for word in response.split():
            yield word + " "
    
    async def get_models(self) -> List[Dict[str, Any]]:
        return [{"name": "echo", "size": 0, "modified_at": "2025-01-19T00:00:00Z"}]
    
    async def health_check(self) -> bool:
        return True 