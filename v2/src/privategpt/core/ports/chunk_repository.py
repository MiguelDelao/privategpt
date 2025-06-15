from __future__ import annotations

from typing import Protocol, List

from privategpt.core.domain.chunk import Chunk


class ChunkRepositoryPort(Protocol):
    async def add_many(self, chunks: List[Chunk]) -> None: ...

    async def list_by_document(self, document_id: int) -> List[Chunk]: ...

    async def list_by_ids(self, ids: List[int]) -> List[Chunk]: ... 