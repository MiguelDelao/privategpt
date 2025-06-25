from __future__ import annotations

from typing import Iterable

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.core.domain.document import Document, DocumentStatus
from privategpt.core.ports.document_repository import DocumentRepositoryPort
from privategpt.infra.database import models


class SqlDocumentRepository(DocumentRepositoryPort):
    """Async SQLAlchemy implementation of DocumentRepositoryPort."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, doc: Document) -> Document:
        db_obj = models.Document(
            title=doc.title,
            file_path=doc.file_path,
            uploaded_at=doc.uploaded_at,
            status=doc.status.value,
            error=doc.error,
        )
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        doc.id = db_obj.id
        return doc

    async def get(self, doc_id: int) -> Document | None:
        result = await self.session.execute(select(models.Document).where(models.Document.id == doc_id))
        row = result.scalar_one_or_none()
        if row:
            return Document(
                id=row.id,
                collection_id=row.collection_id,
                user_id=row.user_id,
                title=row.title,
                file_path=row.file_path,
                file_name=row.file_name,
                file_size=row.file_size,
                mime_type=row.mime_type,
                uploaded_at=row.uploaded_at,
                status=DocumentStatus(row.status),
                error=row.error,
                task_id=row.task_id,
                processing_progress=row.processing_progress or {},
                doc_metadata=row.doc_metadata or {}
            )
        return None

    async def list(self) -> Iterable[Document]:
        result = await self.session.execute(select(models.Document))
        for row in result.scalars():
            yield Document(
                id=row.id,
                collection_id=row.collection_id,
                user_id=row.user_id,
                title=row.title,
                file_path=row.file_path,
                file_name=row.file_name,
                file_size=row.file_size,
                mime_type=row.mime_type,
                uploaded_at=row.uploaded_at,
                status=DocumentStatus(row.status),
                error=row.error,
                task_id=row.task_id,
                processing_progress=row.processing_progress or {},
                doc_metadata=row.doc_metadata or {}
            )

    async def update(self, doc: Document) -> None:
        await self.session.execute(
            update(models.Document)
            .where(models.Document.id == doc.id)
            .values(
                status=doc.status.value, 
                error=doc.error,
                task_id=doc.task_id,
                processing_progress=doc.processing_progress,
                doc_metadata=doc.doc_metadata
            )
        )
        await self.session.commit() 