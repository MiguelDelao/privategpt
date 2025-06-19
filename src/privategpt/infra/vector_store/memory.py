from __future__ import annotations

from typing import Sequence, List, Tuple, Dict
import numpy as np

from privategpt.core.ports.vector_store import VectorStorePort
from privategpt.shared.logging import get_logger

logger = get_logger("vector.memory")


class InMemoryVectorStore(VectorStorePort):
    def __init__(self):
        self._store: Dict[str, Sequence[float]] = {}

    async def add_vectors(self, embeddings: List[Sequence[float]], metadatas: List[dict], ids: List[str]) -> None:
        logger.info("vector.add", adapter="memory", count=len(ids))
        for eid, emb in zip(ids, embeddings):
            self._store[eid] = emb

    async def similarity_search(
        self,
        embedding: Sequence[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> List[Tuple[str, float]]:
        logger.info("vector.search", adapter="memory", top_k=top_k, store_size=len(self._store))
        if not self._store:
            return []
        query = np.array(embedding)
        results: List[Tuple[str, float]] = []
        for k, v in self._store.items():
            score = float(np.dot(query, v) / (np.linalg.norm(query) * np.linalg.norm(v)))
            results.append((k, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k] 