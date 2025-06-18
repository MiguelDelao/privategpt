from __future__ import annotations

"""Celery application & tasks for background ingestion."""

from celery import Celery, current_task
from privategpt.shared.settings import settings  # type: ignore
from privategpt.infra.tasks.service_factory import build_rag_service
from privategpt.core.domain.document import DocumentStatus
from privategpt.infra.database.async_session import AsyncSessionLocal
from privategpt.infra.database.document_repository import SqlDocumentRepository
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

app = Celery(
    "rag",
    broker=settings.redis_url or "redis://redis:6379/0",
    backend=settings.redis_url or "redis://redis:6379/1",
)


@app.task(name="ingest_document")
def ingest_document_task(doc_id: int, file_path: str, title: str, text: str):
    """Background ingestion task – split, embed, vector-store, save chunks."""

    async def _run():
        async with AsyncSessionLocal() as session:  # type: AsyncSession
            repo = SqlDocumentRepository(session)
            rag = build_rag_service(session)

            try:
                await rag.ingest_document(title, file_path, text)
                doc = await repo.get(doc_id)
                if doc:
                    doc.status = DocumentStatus.COMPLETE
                    await repo.update(doc)
            except Exception as exc:  # noqa: BLE001
                doc = await repo.get(doc_id)
                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.error = str(exc)
                    await repo.update(doc)
                raise

    asyncio.run(_run()) 