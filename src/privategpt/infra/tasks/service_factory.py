from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.infra.database.document_repository import SqlDocumentRepository
from privategpt.infra.database.chunk_repository import SqlChunkRepository
from privategpt.infra.splitters.simple import SimpleSplitterAdapter
from privategpt.infra.embedder.bge_adapter import BgeEmbedderAdapter
from privategpt.infra.vector_store.weaviate_adapter import WeaviateAdapter
from privategpt.services.rag.core.service import RagService
from privategpt.infra.chat.echo import EchoChatAdapter


def build_rag_service(session: AsyncSession) -> RagService:  # noqa: D401
    """Assemble a `RagService` with production adapters."""

    splitter = SimpleSplitterAdapter()
    embedder = BgeEmbedderAdapter()
    vector_store = WeaviateAdapter()
    doc_repo = SqlDocumentRepository(session)
    chunk_repo = SqlChunkRepository(session)
    chat_llm = EchoChatAdapter()  # replace with real LLM adapter later

    return RagService(doc_repo, splitter, embedder, vector_store, chunk_repo, chat_llm) 