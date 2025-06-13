from __future__ import annotations

"""Domain entity representing a *logical* document stored by PrivateGPT.

This object is framework-agnostic: no Pydantic, SQLAlchemy or Weaviate SDK
imports – just pure Python types.  That makes it trivial to unit-test and fit
into an LLM context window.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
import uuid


@dataclass(slots=True)
class Document:
    """Immutable snapshot of a stored document."""

    id: str
    filename: str
    content: str
    content_type: str = "text/plain"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def size(self) -> int:
        """Return raw length of *content* in bytes (utf-8)."""

        return len(self.content.encode())

    def chunks(self, chunk_size: int = 1024) -> List[str]:
        """Yield naive fixed-size text chunks (to be replaced by smart splitter)."""

        return [self.content[i : i + chunk_size] for i in range(0, len(self.content), chunk_size)]

    @classmethod
    def new(
        cls,
        *,
        filename: str,
        content: str,
        content_type: str = "text/plain",
        metadata: Dict[str, Any] | None = None,
    ) -> "Document":
        """Factory that assigns a UUID v4."""

        return cls(
            id=str(uuid.uuid4()),
            filename=filename,
            content=content,
            content_type=content_type,
            metadata=metadata or {},
        ) 