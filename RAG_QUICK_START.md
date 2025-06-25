# RAG & MCP Integration - Quick Start Guide

## 🎯 Core Concept

Build a knowledge management system where users can:
1. Create **collections and folders** (hierarchical organization) for different contexts
2. Upload documents that get processed asynchronously
3. Use **@ mentions** in chat to specify which context the AI should use
4. MCP tools can search and access these knowledge bases

## 🏗️ Key Architectural Decisions

### 1. Collection & Folder Model
- **What**: Hierarchical document organization (e.g., "Cases" > "Smith v Jones" > "Discovery")
- **Why**: Users need familiar folder structure to organize knowledge
- **How**: Self-referential table with parent_id, cached paths, and depth tracking

### 2. Async Document Processing
- **What**: Celery tasks process documents in background
- **Why**: Large documents take time to chunk and embed
- **How**: SSE streams progress updates to frontend in real-time

### 3. @ Mention Context System
- **What**: Type `@Cases` or `@Cases/Smith` to control search scope
- **Why**: Precise context control for better AI responses
- **How**: Frontend sends collection paths, backend filters vector search

### 4. MCP Tool Integration
- **What**: Tools that can search/access RAG knowledge bases
- **Why**: AI needs programmatic access to user's documents
- **How**: `search_knowledge` tool with workspace/document filtering

## 📝 Immediate Action Items

### 1. Database Schema (Start Here!)
```sql
-- Add to your next migration
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    collection_type VARCHAR DEFAULT 'folder', -- 'collection' for root, 'folder' for nested
    path VARCHAR NOT NULL, -- Cached full path like '/Cases/Smith v Jones'
    depth INTEGER DEFAULT 0,
    icon VARCHAR DEFAULT '📁',
    color VARCHAR DEFAULT '#3B82F6',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    UNIQUE(user_id, parent_id, name)
);

ALTER TABLE documents ADD COLUMN collection_id UUID REFERENCES collections(id);
ALTER TABLE chunks ADD COLUMN collection_id UUID REFERENCES collections(id);

-- Indexes for efficient navigation
CREATE INDEX idx_collections_parent ON collections(parent_id);
CREATE INDEX idx_collections_path ON collections(path);
```

### 2. First API Endpoints
```python
# In rag_router.py
@router.post("/collections")
async def create_collection(
    collection: CollectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Build path based on parent
    # Create collection/folder
    # Return with full path

@router.get("/collections/{id}/children")
async def list_children(
    id: UUID,
    user: User = Depends(get_current_user)
):
    # Return sub-folders and documents
```

### 3. Document Upload Update
```python
# Update existing upload endpoint
@router.post("/collections/{collection_id}/documents")
async def upload_document(
    collection_id: str,
    file: UploadFile,
    background_tasks: BackgroundTasks
):
    # Validate collection ownership
    # Create document record with collection_id
    # Queue Celery task
    # Return document ID for progress tracking
```

### 4. Progress Streaming
```python
# New endpoint in gateway
@router.get("/api/rag/documents/{id}/progress")
async def stream_progress(id: str):
    async def generate():
        # Subscribe to Redis channel
        # Yield SSE events
    return StreamingResponse(generate(), media_type="text/event-stream")
```

## 🚀 Development Sequence

1. **Week 1**: Get collections & folders working
   - Database schema with hierarchy ✓
   - CRUD APIs with navigation ✓
   - Folder tree UI ✓

2. **Week 2**: Document processing
   - Celery pipeline ✓
   - Progress tracking ✓
   - Frontend upload UI ✓

3. **Week 3**: MCP integration
   - Search tool ✓
   - Tool factory ✓
   - Testing ✓

4. **Week 4**: Polish
   - @ mentions ✓
   - Performance ✓
   - Documentation ✓

## 💡 Pro Tips

1. **Start Simple**: Get basic workspace CRUD working first
2. **Test Early**: Use Postman/curl to test APIs before frontend
3. **Mock First**: Mock the Celery tasks initially, add processing later
4. **Incremental**: Each phase builds on the previous one

## 🔧 Quick Test Commands

```bash
# Create a root collection
curl -X POST localhost:8000/api/rag/collections \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Cases", "description": "Legal case documents"}'

# Create a sub-folder
curl -X POST localhost:8000/api/rag/collections \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Smith v Jones", "parent_id": "<collection-id>"}'

# Upload a document to a folder
curl -X POST localhost:8000/api/rag/collections/{folder-id}/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf"

# Watch progress
curl -N localhost:8000/api/rag/documents/{id}/progress \
  -H "Authorization: Bearer $TOKEN"
```

## 🎨 Frontend Components Needed

1. **CollectionBrowser**: Tree view to navigate folders
2. **DocumentUploader**: Drag-drop with progress bar
3. **ContextMention**: @ symbol trigger with path support (@Cases/Smith)
4. **FolderView**: Show current folder contents with breadcrumb

Remember: The goal is to make document management feel seamless while giving users precise control over what context their AI uses!