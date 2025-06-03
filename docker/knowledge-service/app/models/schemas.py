"""
Pydantic Data Models for Knowledge Service API
Clean, type-safe request/response schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# ================================
# DOCUMENT MODELS
# ================================

class DocumentUploadRequest(BaseModel):
    """Upload a new document for processing"""
    content: str = Field(..., description="Full document text")
    filename: str = Field(..., description="Original filename") 
    content_type: str = Field(default="text/plain", description="MIME type")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Custom metadata")

class DocumentChunk(BaseModel):
    """Single processed document chunk"""
    id: str                           # Unique chunk identifier
    content: str                      # Chunk text content
    metadata: Dict[str, Any]          # Chunk metadata
    document_id: str                  # Parent document ID
    chunk_index: int                  # Position in document

class DocumentResponse(BaseModel):
    """Document information after processing"""
    id: str                           # Document ID
    filename: str                     # Original filename
    content_type: str                 # MIME type
    size: int                         # Content size in bytes
    chunk_count: int                  # Number of chunks created
    created_at: datetime              # Upload timestamp
    metadata: Dict[str, Any]          # Document metadata

class DocumentListResponse(BaseModel):
    """Paginated list of documents"""
    documents: List[DocumentResponse] # Document array
    total: int                        # Total count
    page: int                         # Current page
    page_size: int                    # Items per page

# ================================
# SEARCH MODELS  
# ================================

class SearchRequest(BaseModel):
    """Semantic search request"""
    query: str = Field(..., description="Search query text")
    limit: Optional[int] = Field(default=10, le=100, description="Max results")
    filters: Optional[Dict[str, Any]] = Field(default={}, description="Metadata filters")
    threshold: Optional[float] = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")

class SearchResult(BaseModel):
    """Single search result with relevance score"""
    content: str                      # Matching text content
    metadata: Dict[str, Any]          # Chunk metadata
    score: float                      # Similarity score (0-1)
    document_id: str                  # Source document ID
    chunk_id: str                     # Source chunk ID

class SearchResponse(BaseModel):
    """Search results with performance info"""
    results: List[SearchResult]       # Matching results
    query: str                        # Original query
    total_results: int                # Number of results
    took_ms: int                      # Search duration

# ================================
# CHAT MODELS
# ================================

class ChatMessage(BaseModel):
    """Single conversation message"""
    role: str = Field(..., description="user, assistant, or system")
    content: str = Field(..., description="Message text")

class ChatRequest(BaseModel):
    """RAG chat conversation request"""
    messages: List[ChatMessage] = Field(..., description="Conversation history")
    max_tokens: Optional[int] = Field(default=1000, le=4000, description="Response limit")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Creativity (0-2)")
    search_limit: Optional[int] = Field(default=5, le=20, description="Context documents")
    include_sources: Optional[bool] = Field(default=True, description="Show sources")

class ChatResponse(BaseModel):
    """RAG chat response with sources"""
    model_config = ConfigDict(protected_namespaces=())
    
    message: ChatMessage              # AI response message
    sources: Optional[List[SearchResult]] = None  # Source documents used
    took_ms: int                      # Response time
    model_used: str                   # LLM model name

# ================================
# SYSTEM MODELS
# ================================

class HealthResponse(BaseModel):
    """Service health status"""
    service: str                      # Service name
    status: str                       # healthy/degraded/down
    components: Dict[str, str]        # Component status map
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str                        # Error type
    message: str                      # Human-readable message
    timestamp: datetime = Field(default_factory=datetime.utcnow) 