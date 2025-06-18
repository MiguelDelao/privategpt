from __future__ import annotations

from typing import Protocol, Sequence, List


class EmbedderPort(Protocol):
    async def embed_documents(self, texts: List[str]) -> List[Sequence[float]]: ...

    async def embed_query(self, text: str) -> Sequence[float]: ... 