from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(slots=True)
class Document:
    id: int | None
    title: str
    file_path: str
    uploaded_at: datetime
    status: DocumentStatus = DocumentStatus.PENDING
    error: Optional[str] = None 