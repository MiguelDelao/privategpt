from __future__ import annotations

from typing import List
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from privategpt.core.domain.chunk import Chunk
from privategpt.core.ports.chunk_repository import ChunkRepositoryPort
from privategpt.infra.database import models


class SqlChunkRepository(ChunkRepositoryPort):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_many(self, chunks: List[Chunk]) -> None:
        objs = [
            models.Chunk(
                document_id=c.document_id,
                position=c.position,
                text=c.text,
                embedding=json.dumps(c.embedding) if c.embedding else None,
            )
            for c in chunks
        ]
        self.session.add_all(objs)
        await self.session.commit()

    async def list_by_document(self, document_id: int) -> List[Chunk]:
        result = await self.session.execute(select(models.Chunk).where(models.Chunk.document_id == document_id))
        return [
            Chunk(
                id=row.id,
                document_id=row.document_id,
                position=row.position,
                text=row.text,
                embedding=json.loads(row.embedding) if row.embedding else None,
            )
            for row in result.scalars()
        ]

    async def list_by_ids(self, ids: List[int]) -> List[Chunk]:
        if not ids:
            return []
        result = await self.session.execute(select(models.Chunk).where(models.Chunk.id.in_(ids)))
        return [
            Chunk(
                id=row.id,
                document_id=row.document_id,
                position=row.position,
                text=row.text,
                embedding=json.loads(row.embedding) if row.embedding else None,
            )
            for row in result.scalars()
        ]
    
    async def get_by_document_and_positions(self, doc_positions: List[Tuple[int, int]]) -> List[Chunk]:
        """Get chunks by (document_id, position) pairs."""
        if not doc_positions:
            return []
        
        from sqlalchemy import or_, and_
        
        conditions = [
            and_(models.Chunk.document_id == doc_id, models.Chunk.position == pos)
            for doc_id, pos in doc_positions
        ]
        
        result = await self.session.execute(
            select(models.Chunk).where(or_(*conditions))
        )
        
        return [
            Chunk(
                id=row.id,
                document_id=row.document_id,
                position=row.position,
                text=row.text,
                embedding=json.loads(row.embedding) if row.embedding else None,
            )
            for row in result.scalars()
        ] 