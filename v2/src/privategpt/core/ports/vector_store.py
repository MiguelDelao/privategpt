from __future__ import annotations

from typing import Protocol, Sequence, List, Tuple


class VectorStorePort(Protocol):
    async def add_vectors(self, embeddings: List[Sequence[float]], metadatas: List[dict], ids: List[str]) -> None: ...

    async def similarity_search(
        self,
        embedding: Sequence[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> List[Tuple[str, float]]: ...  # returns (id, score) 