from __future__ import annotations

import hashlib
from typing import Sequence, List

from privategpt.core.ports.embedder import EmbedderPort
from privategpt.shared.logging import get_logger

logger = get_logger("embedder.fake")


class FakeEmbedderAdapter(EmbedderPort):
    """Deterministic but trivial embedding: hash text into fixed-length vector."""

    def _hash(self, text: str) -> Sequence[float]:
        h = hashlib.sha256(text.encode()).digest()
        # produce 32 floats between 0 and 1
        return [b / 255 for b in h]

    async def embed_documents(self, texts: List[str]) -> List[Sequence[float]]:
        logger.info("chunk.embed", adapter="fake", batch=len(texts))
        return [self._hash(t) for t in texts]

    async def embed_query(self, text: str) -> Sequence[float]:
        logger.info("query.embed", adapter="fake")
        return self._hash(text) 