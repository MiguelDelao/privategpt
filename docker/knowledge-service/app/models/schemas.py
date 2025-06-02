"""
Pydantic models for request/response schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class DocumentUploadRequest(BaseModel):
    """Request model for document upload"""
    content: str = Field(..., description="Document content")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(default="text/plain", description="MIME type")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")


class DocumentChunk(BaseModel):
    """Individual document chunk"""
    id: str
    content: str
    metadata: Dict[str, Any]
    document_id: str
    chunk_index: int


class DocumentResponse(BaseModel):
    """Response model for document operations"""
    id: str
    filename: str
    content_type: str
    size: int
    chunk_count: int
    created_at: datetime
    metadata: Dict[str, Any]


class DocumentListResponse(BaseModel):
    """Response model for listing documents"""
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int


class SearchRequest(BaseModel):
    """Request model for vector search"""
    query: str = Field(..., description="Search query text")
    limit: Optional[int] = Field(default=10, le=100, description="Maximum results")
    filters: Optional[Dict[str, Any]] = Field(default={}, description="Metadata filters")
    threshold: Optional[float] = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")


class SearchResult(BaseModel):
    """Individual search result"""
    content: str
    metadata: Dict[str, Any]
    score: float
    document_id: str
    chunk_id: str


class SearchResponse(BaseModel):
    """Response model for search operations"""
    results: List[SearchResult]
    query: str
    total_results: int
    took_ms: int


class ChatMessage(BaseModel):
    """Chat message"""
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for RAG chat"""
    messages: List[ChatMessage] = Field(..., description="Conversation history")
    max_tokens: Optional[int] = Field(default=1000, le=4000, description="Maximum response tokens")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Response temperature")
    search_limit: Optional[int] = Field(default=5, le=20, description="Context documents to retrieve")
    include_sources: Optional[bool] = Field(default=True, description="Include source references")


class ChatResponse(BaseModel):
    """Response model for chat operations"""
    model_config = ConfigDict(protected_namespaces=())
    
    message: ChatMessage
    sources: Optional[List[SearchResult]] = None
    took_ms: int
    model_used: str


class HealthResponse(BaseModel):
    """Health check response"""
    service: str
    status: str
    components: Dict[str, str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow) 