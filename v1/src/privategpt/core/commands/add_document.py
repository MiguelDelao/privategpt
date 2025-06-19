from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..domain.document import Document
from ..ports.document_repository import DocumentRepository
from ..ports.embedding_provider import EmbeddingProvider
from ..ports.text_splitter import TextSplitter


@dataclass(slots=True)
class AddDocumentCommand:
    filename: str
    content: str
    content_type: str = "text/plain"
    metadata: dict | None = None


class AddDocumentHandler:
    """Application service orchestrating new-document ingestion."""

    def __init__(
        self,
        *,
        repo: DocumentRepository,
        splitter: TextSplitter,
        embedder: EmbeddingProvider,
    ) -> None:
        self._repo = repo
        self._splitter = splitter
        self._embedder = embedder

    async def __call__(self, cmd: AddDocumentCommand) -> Document:
        # 1. Create domain object
        doc = Document.new(
            filename=cmd.filename,
            content=cmd.content,
            content_type=cmd.content_type,
            metadata=cmd.metadata,
        )

        # 2. Split & embed
        chunks = self._splitter.split(doc.content)
        vectors = await self._embedder.embed(chunks)

        # Note: persistence layer expected to handle chunks + vectors – this keeps
        # the core clean. We assume repo.save will store vectors appropriately.
        await self._repo.save(doc)

        return doc 