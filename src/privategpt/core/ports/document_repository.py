from __future__ import annotations

from typing import Protocol, Iterable

from privategpt.core.domain.document import Document


class DocumentRepositoryPort(Protocol):
    """Repository abstraction for Document persistence."""

    async def add(self, doc: Document) -> Document: ...

    async def get(self, doc_id: int) -> Document | None: ...

    async def list(self) -> Iterable[Document]: ...

    async def update(self, doc: Document) -> None: ... 