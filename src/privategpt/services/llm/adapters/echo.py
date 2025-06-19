from __future__ import annotations

from privategpt.services.llm.core import LLMPort


class EchoAdapter(LLMPort):
    async def generate(self, prompt: str) -> str:  # noqa: D401
        return f"Echo: {prompt}" 