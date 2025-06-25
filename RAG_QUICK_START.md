# RAG & MCP Integration - Quick Start Guide

## 🎯 Core Concept

Build a knowledge management system where users can:
1. Create **workspaces** (knowledge silos) for different contexts
2. Upload documents that get processed asynchronously
3. Use **@ mentions** in chat to specify which context the AI should use
4. MCP tools can search and access these knowledge bases

## 🏗️ Key Architectural Decisions

### 1. Workspace Model
- **What**: Isolated document collections (e.g., "Legal Cases", "Research Papers")
- **Why**: Users need to separate different types of knowledge
- **How**: Each workspace has its own vector namespace in Weaviate

### 2. Async Document Processing
- **What**: Celery tasks process documents in background
- **Why**: Large documents take time to chunk and embed
- **How**: SSE streams progress updates to frontend in real-time

### 3. @ Mention Context System
- **What**: Type `@cases` to make AI search only in cases workspace
- **Why**: Precise context control for better AI responses
- **How**: Frontend sends context metadata, backend filters vector search

### 4. MCP Tool Integration
- **What**: Tools that can search/access RAG knowledge bases
- **Why**: AI needs programmatic access to user's documents
- **How**: `search_knowledge` tool with workspace/document filtering

## 📝 Immediate Action Items

### 1. Database Schema (Start Here!)
```sql
-- Add to your next migration
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT,
    icon VARCHAR DEFAULT '📁',
    color VARCHAR DEFAULT '#3B82F6',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

ALTER TABLE documents ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE chunks ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
```

### 2. First API Endpoint
```python
# In rag_router.py
@router.post("/workspaces")
async def create_workspace(
    workspace: WorkspaceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Create workspace for user
    # Return workspace details
```

### 3. Document Upload Update
```python
# Update existing upload endpoint
@router.post("/workspaces/{workspace_id}/documents")
async def upload_document(
    workspace_id: str,
    file: UploadFile,
    background_tasks: BackgroundTasks
):
    # Validate workspace ownership
    # Create document record
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

1. **Week 1**: Get workspaces working
   - Database schema ✓
   - CRUD APIs ✓
   - Basic frontend UI ✓

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
# Create a workspace
curl -X POST localhost:8000/api/rag/workspaces \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Cases", "description": "Legal case documents"}'

# Upload a document
curl -X POST localhost:8000/api/rag/workspaces/{id}/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf"

# Watch progress
curl -N localhost:8000/api/rag/documents/{id}/progress \
  -H "Authorization: Bearer $TOKEN"
```

## 🎨 Frontend Components Needed

1. **WorkspaceSelector**: Dropdown/sidebar to switch workspaces
2. **DocumentUploader**: Drag-drop with progress bar
3. **ContextMention**: @ symbol trigger for workspace selection
4. **DocumentList**: Show documents in current workspace

Remember: The goal is to make document management feel seamless while giving users precise control over what context their AI uses!