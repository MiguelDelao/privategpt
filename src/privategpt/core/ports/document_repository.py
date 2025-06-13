from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Protocol

from ..domain.document import Document


class DocumentRepository(Protocol):  # noqa: D401 – interface
    """Persistence operations for Document domain objects."""

    @abstractmethod
    async def save(self, document: Document) -> None:  # noqa: D401 – imperative
        ...

    @abstractmethod
    async def delete(self, document_id: str) -> None:
        ...

    @abstractmethod
    async def get(self, document_id: str) -> Document | None:
        ...

    @abstractmethod
    async def search(self, query_embedding: list[float], *, limit: int = 10, threshold: float = 0.7) -> List[Document]:
        ... 