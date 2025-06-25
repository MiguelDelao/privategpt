# RAG Service Implementation Plan

## Current State Analysis

### ✅ What Already Exists
1. **Basic Document Management**
   - Document upload endpoint (`POST /rag/documents`)
   - Document status tracking (pending, processing, complete, failed)
   - Celery task for async processing
   - Simple text-based document ingestion

2. **Vector Storage**
   - Weaviate integration
   - Document chunking and embedding
   - Basic similarity search

3. **Chat Functionality**
   - RAG chat endpoint (`POST /rag/chat`)
   - Simple Q&A with citations

### ❌ What's Missing
1. **Workspace Support**
   - No workspace/knowledge silo concept
   - No document organization
   - No user-specific namespacing

2. **Advanced Document Processing**
   - No file upload support (only text)
   - No progress streaming
   - No document metadata

3. **MCP Integration**
   - No tool interface for RAG
   - No context filtering
   - No workspace-aware search

## Implementation Steps

### Step 1: Database Schema Updates
```sql
-- 1. Create workspace table
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(50) DEFAULT '📁',
    color VARCHAR(7) DEFAULT '#3B82F6',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    UNIQUE(user_id, name)
);

-- 2. Add workspace support to existing tables
ALTER TABLE documents 
ADD COLUMN workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
ADD COLUMN file_name VARCHAR(255),
ADD COLUMN file_size INTEGER,
ADD COLUMN mime_type VARCHAR(100),
ADD COLUMN processing_progress JSONB DEFAULT '{}',
ADD COLUMN metadata JSONB DEFAULT '{}';

ALTER TABLE chunks
ADD COLUMN workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;

-- 3. Create indexes
CREATE INDEX idx_documents_workspace ON documents(workspace_id);
CREATE INDEX idx_documents_user ON documents(user_id);
CREATE INDEX idx_chunks_workspace ON chunks(workspace_id);
```

### Step 2: Update Domain Models
```python
# src/privategpt/core/domain/workspace.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

@dataclass
class Workspace:
    id: Optional[UUID]
    user_id: int
    name: str
    description: Optional[str] = None
    icon: str = "📁"
    color: str = "#3B82F6"
    settings: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}

# Update Document model
@dataclass
class Document:
    id: Optional[int]
    workspace_id: UUID
    user_id: int
    title: str
    file_path: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    status: DocumentStatus = DocumentStatus.PENDING
    error: Optional[str] = None
    processing_progress: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    uploaded_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.processing_progress is None:
            self.processing_progress = {}
        if self.metadata is None:
            self.metadata = {}
```

### Step 3: Create Workspace Repository
```python
# src/privategpt/infra/database/workspace_repository.py
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.core.domain.workspace import Workspace
from privategpt.infra.database.models import Workspace as WorkspaceModel

class WorkspaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, workspace: Workspace) -> Workspace:
        db_workspace = WorkspaceModel(
            user_id=workspace.user_id,
            name=workspace.name,
            description=workspace.description,
            icon=workspace.icon,
            color=workspace.color,
            settings=workspace.settings
        )
        self.session.add(db_workspace)
        await self.session.commit()
        await self.session.refresh(db_workspace)
        return self._to_domain(db_workspace)
    
    async def get_by_id(self, workspace_id: UUID, user_id: int) -> Optional[Workspace]:
        result = await self.session.execute(
            select(WorkspaceModel).where(
                and_(
                    WorkspaceModel.id == workspace_id,
                    WorkspaceModel.user_id == user_id,
                    WorkspaceModel.deleted_at.is_(None)
                )
            )
        )
        db_workspace = result.scalar_one_or_none()
        return self._to_domain(db_workspace) if db_workspace else None
    
    async def list_by_user(self, user_id: int) -> List[Workspace]:
        result = await self.session.execute(
            select(WorkspaceModel).where(
                and_(
                    WorkspaceModel.user_id == user_id,
                    WorkspaceModel.deleted_at.is_(None)
                )
            ).order_by(WorkspaceModel.name)
        )
        return [self._to_domain(w) for w in result.scalars()]
    
    def _to_domain(self, db_model: WorkspaceModel) -> Workspace:
        return Workspace(
            id=db_model.id,
            user_id=db_model.user_id,
            name=db_model.name,
            description=db_model.description,
            icon=db_model.icon,
            color=db_model.color,
            settings=db_model.settings,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
            deleted_at=db_model.deleted_at
        )
```

### Step 4: Update RAG Router with Workspace Support
```python
# src/privategpt/services/rag/api/rag_router.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from typing import List, Optional
from uuid import UUID

# ... existing imports ...

# New endpoints for workspaces
@router.post("/workspaces", response_model=WorkspaceOut)
async def create_workspace(
    workspace: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    repo = WorkspaceRepository(session)
    new_workspace = Workspace(
        id=None,
        user_id=current_user.id,
        name=workspace.name,
        description=workspace.description,
        icon=workspace.icon,
        color=workspace.color,
        settings=workspace.settings
    )
    return await repo.create(new_workspace)

@router.get("/workspaces", response_model=List[WorkspaceOut])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    repo = WorkspaceRepository(session)
    return await repo.list_by_user(current_user.id)

# Updated document upload with file support
@router.post("/workspaces/{workspace_id}/documents")
async def upload_document(
    workspace_id: UUID,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    # Validate workspace ownership
    workspace_repo = WorkspaceRepository(session)
    workspace = await workspace_repo.get_by_id(workspace_id, current_user.id)
    if not workspace:
        raise HTTPException(404, "Workspace not found")
    
    # Save file to storage
    file_path = await save_uploaded_file(file)
    
    # Create document record
    doc_repo = SqlDocumentRepository(session)
    new_doc = Document(
        id=None,
        workspace_id=workspace_id,
        user_id=current_user.id,
        title=file.filename,
        file_path=file_path,
        file_name=file.filename,
        file_size=file.size,
        mime_type=file.content_type,
        status=DocumentStatus.PENDING,
        uploaded_at=datetime.utcnow()
    )
    doc = await doc_repo.add(new_doc)
    
    # Queue processing task
    task_queue = CeleryTaskQueueAdapter()
    task_id = task_queue.enqueue(
        "process_document_with_progress",
        str(doc.id),
        str(workspace_id),
        file_path
    )
    
    return {
        "document_id": doc.id,
        "task_id": task_id,
        "status": "processing"
    }

# Progress streaming endpoint
@router.get("/documents/{document_id}/progress")
async def stream_document_progress(
    document_id: int,
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis)
):
    async def event_generator():
        channel = f"doc_progress:{document_id}:{current_user.id}"
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message and message['type'] == 'message':
                    yield f"data: {message['data'].decode()}\n\n"
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
```

### Step 5: Enhanced Celery Task with Progress
```python
# src/privategpt/infra/tasks/document_tasks.py
from celery import current_task
import redis
import json

@celery_app.task(bind=True)
def process_document_with_progress(self, document_id: str, workspace_id: str, file_path: str):
    """Process document with real-time progress updates"""
    redis_client = redis.Redis.from_url(settings.redis_url)
    
    def update_progress(status: str, percentage: int, message: str = "", error: str = None):
        progress = {
            "document_id": document_id,
            "status": status,
            "percentage": percentage,
            "message": message,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Update database
        with get_sync_session() as session:
            repo = SyncDocumentRepository(session)
            doc = repo.get(int(document_id))
            if doc:
                doc.processing_progress = progress
                doc.status = status
                if error:
                    doc.error = error
                repo.update(doc)
        
        # Publish to Redis for SSE
        channel = f"doc_progress:{document_id}:*"
        redis_client.publish(channel, json.dumps(progress))
    
    try:
        # Step 1: Load document
        update_progress("loading", 10, "Loading document...")
        content = load_document_content(file_path)
        
        # Step 2: Split into chunks
        update_progress("chunking", 30, "Splitting document into chunks...")
        chunks = split_document(content)
        total_chunks = len(chunks)
        
        # Step 3: Generate embeddings
        update_progress("embedding", 50, f"Generating embeddings for {total_chunks} chunks...")
        embeddings = []
        for i, chunk in enumerate(chunks):
            embedding = generate_embedding(chunk)
            embeddings.append(embedding)
            
            # Update progress for each chunk
            progress_pct = 50 + int((i + 1) / total_chunks * 40)
            update_progress(
                "embedding",
                progress_pct,
                f"Processed chunk {i + 1}/{total_chunks}"
            )
        
        # Step 4: Store in vector database
        update_progress("storing", 90, "Storing in vector database...")
        store_in_weaviate(workspace_id, document_id, chunks, embeddings)
        
        # Step 5: Complete
        update_progress("completed", 100, "Document processing complete!")
        
    except Exception as e:
        update_progress("failed", 0, error=str(e))
        raise
```

### Step 6: MCP Tool Implementation
```python
# src/privategpt/services/mcp/tools/rag_search_tool.py
from typing import Dict, List, Optional
from uuid import UUID

class RAGSearchTool:
    """MCP tool for searching RAG knowledge bases"""
    
    name = "search_knowledge"
    description = "Search through uploaded documents in specified workspaces"
    
    def __init__(self, rag_service_url: str):
        self.rag_service_url = rag_service_url
    
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "workspace_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of workspace IDs to search in"
                },
                "document_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific document IDs to search in"
                },
                "max_results": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum number of results"
                },
                "include_metadata": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include document metadata in results"
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, **params) -> Dict:
        # Build search filters
        filters = {}
        if params.get("workspace_ids"):
            filters["workspace_id"] = {"$in": params["workspace_ids"]}
        if params.get("document_ids"):
            filters["document_id"] = {"$in": params["document_ids"]}
        
        # Perform vector search
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.rag_service_url}/api/rag/search",
                json={
                    "query": params["query"],
                    "filters": filters,
                    "limit": params.get("max_results", 5)
                }
            )
            results = response.json()
        
        # Format results
        formatted_results = []
        for result in results["results"]:
            formatted = {
                "content": result["content"],
                "score": result["score"],
                "document_title": result["document_title"],
                "workspace_name": result["workspace_name"]
            }
            
            if params.get("include_metadata", True):
                formatted["metadata"] = {
                    "document_id": result["document_id"],
                    "workspace_id": result["workspace_id"],
                    "chunk_position": result["chunk_position"],
                    "upload_date": result["upload_date"]
                }
            
            formatted_results.append(formatted)
        
        return {
            "results": formatted_results,
            "total_found": len(formatted_results),
            "query": params["query"]
        }
```

### Step 7: Frontend Context Integration
```typescript
// Frontend types and interfaces
interface WorkspaceContext {
  workspaceIds?: string[]
  documentIds?: string[]
  searchScope: 'workspace' | 'document' | 'all'
}

interface ChatMessage {
  content: string
  context?: WorkspaceContext
  mentions?: MentionedResource[]
}

interface MentionedResource {
  type: 'workspace' | 'document'
  id: string
  name: string
  icon: string
}

// @ Mention component
const ContextMentionInput: React.FC = () => {
  const [mentions, setMentions] = useState<MentionedResource[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  
  const handleAtSymbol = (position: number) => {
    setShowSuggestions(true)
    // Show workspace/document selector
  }
  
  const addMention = (resource: MentionedResource) => {
    setMentions([...mentions, resource])
    // Add visual tag to input
  }
  
  const buildContext = (): WorkspaceContext => {
    return {
      workspaceIds: mentions
        .filter(m => m.type === 'workspace')
        .map(m => m.id),
      documentIds: mentions
        .filter(m => m.type === 'document')
        .map(m => m.id),
      searchScope: mentions.length > 0 ? 'workspace' : 'all'
    }
  }
  
  // Render input with mention tags
}
```

## Testing Strategy

### 1. Unit Tests
```python
# Test workspace creation
async def test_create_workspace():
    workspace = await create_workspace("Legal Cases", user_id=1)
    assert workspace.name == "Legal Cases"
    assert workspace.user_id == 1

# Test document upload
async def test_upload_document_to_workspace():
    workspace = await create_workspace("Test", user_id=1)
    doc = await upload_document(workspace.id, "test.pdf")
    assert doc.workspace_id == workspace.id
```

### 2. Integration Tests
```python
# Test full pipeline
async def test_document_processing_pipeline():
    # Create workspace
    workspace = await create_workspace("Test Workspace", user_id=1)
    
    # Upload document
    doc_id = await upload_document(workspace.id, "sample.pdf")
    
    # Wait for processing
    await wait_for_processing(doc_id)
    
    # Search using MCP tool
    tool = RAGSearchTool()
    results = await tool.execute(
        query="test query",
        workspace_ids=[str(workspace.id)]
    )
    
    assert len(results["results"]) > 0
```

## Migration Path

1. **Week 1**: Database schema + basic workspace CRUD
2. **Week 2**: File upload + Celery processing with progress
3. **Week 3**: MCP tool integration + search improvements
4. **Week 4**: Frontend @ mentions + context selection
5. **Week 5**: Testing + performance optimization

This plan builds incrementally on your existing code while adding the sophisticated features you need for a production-ready RAG system.