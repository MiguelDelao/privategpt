from __future__ import annotations

from typing import Protocol, List

from privategpt.core.domain.chunk import Chunk


class ChatLLMPort(Protocol):
    async def generate_answer(self, question: str, context: List[Chunk]) -> str: ... 