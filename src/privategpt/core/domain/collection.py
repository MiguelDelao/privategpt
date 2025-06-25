"""Collection domain model for hierarchical document organization."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4


@dataclass(slots=True)
class Collection:
    """Represents a collection or folder in the document hierarchy."""
    
    id: Optional[str] = None  # UUID as string
    user_id: int = 0
    parent_id: Optional[str] = None  # UUID as string
    name: str = ""
    description: Optional[str] = None
    collection_type: str = "folder"  # 'collection' for root, 'folder' for nested
    icon: str = "📁"
    color: str = "#3B82F6"
    path: str = ""  # Full path like /Cases/Smith v Jones
    depth: int = 0
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        # Generate UUID if not provided
        if self.id is None:
            self.id = str(uuid4())
        
        # Set collection type based on parent
        if self.parent_id is None:
            self.collection_type = "collection"
            self.depth = 0
            # Build root path if not provided
            if not self.path:
                self.path = f"/{self.name}"
        else:
            self.collection_type = "folder"
            # Depth and path should be set by repository based on parent
    
    @property
    def is_root(self) -> bool:
        """Check if this is a root collection."""
        return self.parent_id is None
    
    @property
    def is_deleted(self) -> bool:
        """Check if this collection is soft-deleted."""
        return self.deleted_at is not None
    
    def get_breadcrumb_parts(self) -> List[str]:
        """Get the parts of the path for breadcrumb display."""
        if not self.path:
            return []
        # Remove leading slash and split
        return self.path.lstrip('/').split('/')


@dataclass(slots=True)
class CollectionSettings:
    """Settings for a collection."""
    
    is_public: bool = False
    default_chunk_size: int = 512
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    retention_days: Optional[int] = None
    auto_process: bool = True  # Automatically process uploaded documents
    allowed_file_types: List[str] = field(default_factory=lambda: ["pdf", "txt", "docx", "md"])
    max_file_size_mb: int = 50
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for storage."""
        return {
            "is_public": self.is_public,
            "default_chunk_size": self.default_chunk_size,
            "embedding_model": self.embedding_model,
            "retention_days": self.retention_days,
            "auto_process": self.auto_process,
            "allowed_file_types": self.allowed_file_types,
            "max_file_size_mb": self.max_file_size_mb
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CollectionSettings:
        """Create settings from dictionary."""
        return cls(
            is_public=data.get("is_public", False),
            default_chunk_size=data.get("default_chunk_size", 512),
            embedding_model=data.get("embedding_model", "BAAI/bge-small-en-v1.5"),
            retention_days=data.get("retention_days"),
            auto_process=data.get("auto_process", True),
            allowed_file_types=data.get("allowed_file_types", ["pdf", "txt", "docx", "md"]),
            max_file_size_mb=data.get("max_file_size_mb", 50)
        )