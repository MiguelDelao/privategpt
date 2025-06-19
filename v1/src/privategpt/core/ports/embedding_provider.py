from __future__ import annotations

from abc import abstractmethod
from typing import List, Protocol


class EmbeddingProvider(Protocol):
    """Return vector representations for text chunks."""

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        ... 