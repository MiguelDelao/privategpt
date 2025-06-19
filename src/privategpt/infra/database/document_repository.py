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
                title=row.title,
                file_path=row.file_path,
                uploaded_at=row.uploaded_at,
                status=DocumentStatus(row.status),
                error=row.error,
            )
        return None

    async def list(self) -> Iterable[Document]:
        result = await self.session.execute(select(models.Document))
        for row in result.scalars():
            yield Document(
                id=row.id,
                title=row.title,
                file_path=row.file_path,
                uploaded_at=row.uploaded_at,
                status=DocumentStatus(row.status),
                error=row.error,
            )

    async def update(self, doc: Document) -> None:
        await self.session.execute(
            update(models.Document)
            .where(models.Document.id == doc.id)
            .values(status=doc.status.value, error=doc.error)
        )
        await self.session.commit() 