from __future__ import annotations

from typing import List

from privategpt.core.domain.document import Document
from privategpt.core.domain.chunk import Chunk
from privategpt.core.domain.query import SearchQuery
from privategpt.core.domain.answer import Answer
from privategpt.core.ports.document_repository import DocumentRepositoryPort
from privategpt.core.ports.text_splitter import TextSplitterPort
from privategpt.core.ports.embedder import EmbedderPort
from privategpt.core.ports.vector_store import VectorStorePort
from privategpt.core.ports.chat_llm import ChatLLMPort
from privategpt.core.ports.chunk_repository import ChunkRepositoryPort


class RagService:
    """Use-case orchestration for RAG ingestion & chat."""

    def __init__(
        self,
        repo: DocumentRepositoryPort,
        splitter: TextSplitterPort,
        embedder: EmbedderPort,
        vector_store: VectorStorePort,
        chunk_repo: ChunkRepositoryPort,
        chat_llm: ChatLLMPort,
    ) -> None:
        self.repo = repo
        self.splitter = splitter
        self.embedder = embedder
        self.vector_store = vector_store
        self.chunk_repo = chunk_repo
        self.chat_llm = chat_llm

    async def ingest_document(self, title: str, file_path: str, text: str) -> Document:
        parts = self.splitter.split(text)
        embeddings = await self.embedder.embed_documents(parts)

        import datetime as _dt

        doc = Document(id=None, title=title, file_path=file_path, uploaded_at=_dt.datetime.utcnow())
        doc = await self.repo.add(doc)

        ids = [f"{doc.id}_{i}" for i in range(len(parts))]
        await self.vector_store.add_vectors(
            embeddings,
            [{"text": p} for p in parts],
            ids,
        )

        chunk_objs = [
            Chunk(id=None, document_id=doc.id, position=i, text=part, embedding=emb)
            for i, (part, emb) in enumerate(zip(parts, embeddings))
        ]
        await self.chunk_repo.add_many(chunk_objs)

        return doc

    async def search(self, query: SearchQuery):
        emb = await self.embedder.embed_query(query.text)
        return await self.vector_store.similarity_search(emb, top_k=query.top_k, filters=query.filters)

    async def chat(self, question: str) -> Answer:
        sim = await self.search(SearchQuery(text=question, top_k=3))
        chunk_ids = [int(s[0].split("_")[-1]) for s in sim]
        chunks = await self.chunk_repo.list_by_ids(chunk_ids)
        answer = await self.chat_llm.generate_answer(question, chunks)
        return Answer(text=answer, citations=[{"chunk_id": s[0], "score": s[1]} for s in sim])
