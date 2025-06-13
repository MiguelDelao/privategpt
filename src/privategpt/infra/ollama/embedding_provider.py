from __future__ import annotations

from typing import List

from privategpt.core.ports.embedding_provider import EmbeddingProvider

try:
    from docker.knowledge_service.app.services.embedding import EmbeddingService  # type: ignore
except ImportError:
    EmbeddingService = None  # type: ignore


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, service: EmbeddingService):  # type: ignore[valid-type]
        self._svc = service

    async def embed(self, texts: List[str]) -> List[List[float]]:  # type: ignore[override]
        if not self._svc:
            raise RuntimeError("EmbeddingService not available")
        return await self._svc.embed(texts) 