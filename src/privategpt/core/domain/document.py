from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Dict, Any


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(slots=True)
class Document:
    id: int | None
    collection_id: Optional[str]  # UUID as string
    user_id: int
    title: str
    file_path: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None  # Size in bytes
    mime_type: Optional[str] = None
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    status: DocumentStatus = DocumentStatus.PENDING
    error: Optional[str] = None
    task_id: Optional[str] = None
    processing_progress: Dict[str, Any] = field(default_factory=dict)
    doc_metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def file_size_mb(self) -> Optional[float]:
        """Get file size in megabytes."""
        if self.file_size is None:
            return None
        return self.file_size / (1024 * 1024)
    
    @property
    def is_processed(self) -> bool:
        """Check if document has been processed."""
        return self.status == DocumentStatus.COMPLETE
    
    @property
    def is_failed(self) -> bool:
        """Check if document processing failed."""
        return self.status == DocumentStatus.FAILED


@dataclass(slots=True)
class ProcessingProgress:
    """Track document processing progress."""
    
    document_id: int
    status: str
    percentage: int
    current_step: str
    chunks_processed: int = 0
    total_chunks: int = 0
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "status": self.status,
            "percentage": self.percentage,
            "current_step": self.current_step,
            "chunks_processed": self.chunks_processed,
            "total_chunks": self.total_chunks,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat()
        } 