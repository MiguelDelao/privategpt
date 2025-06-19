from __future__ import annotations

from typing import List

from privategpt.core.domain.chunk import Chunk
from privategpt.core.ports.chat_llm import ChatLLMPort


class EchoChatAdapter(ChatLLMPort):
    async def generate_answer(self, question: str, context: List[Chunk]) -> str:  # noqa: D401
        joined = " \n".join(c.text for c in context[:3])
        return f"Q: {question}\nBased on: {joined[:200]}..." 