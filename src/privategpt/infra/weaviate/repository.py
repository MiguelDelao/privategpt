from __future__ import annotations

"""Weaviate-backed implementation of `DocumentRepository`."""

import logging
from typing import List

from privategpt.core.domain.document import Document
from privategpt.core.ports.document_repository import DocumentRepository

# We reuse the legacy WeaviateService until further refactor
try:
    from docker.knowledge_service.app.services.weaviate_client import (  # type: ignore
        WeaviateService,
    )
except ImportError:  # pragma: no cover
    WeaviateService = None  # type: ignore

logger = logging.getLogger(__name__)


class WeaviateDocumentRepository(DocumentRepository):
    def __init__(self, service: WeaviateService):  # type: ignore[valid-type]
        self._svc = service

    async def save(self, document: Document) -> None:
        # TODO: use splitting & vectors; placeholder saves metadata only
        logger.info("Persisting document %s via Weaviate", document.id)
        # Implementation deferred

    async def delete(self, document_id: str) -> None:
        if not self._svc:
            return
        try:
            await self._svc.delete_document(document_id)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to delete document %s", document_id)

    async def get(self, document_id: str) -> Document | None:
        if not self._svc:
            return None
        data = await self._svc.get_document_info(document_id)
        if not data:
            return None
        return Document(
            id=data["id"],
            filename=data["filename"],
            content=data.get("content", ""),
            content_type=data.get("content_type", "text/plain"),
            metadata=data.get("metadata", {}),
        )

    async def search(
        self, query_embedding: List[float], *, limit: int = 10, threshold: float = 0.7
    ) -> List[Document]:
        if not self._svc:
            return []
        chunks = await self._svc.search_similar(query_embedding, limit, threshold)
        # Group back to documents – naive mapping for now
        docs: dict[str, Document] = {}
        for ch in chunks:
            if ch["document_id"] not in docs:
                docs[ch["document_id"]] = Document(
                    id=ch["document_id"],
                    filename=ch.get("filename", ""),
                    content="",  # content omitted
                    metadata={},
                )
        return list(docs.values()) 