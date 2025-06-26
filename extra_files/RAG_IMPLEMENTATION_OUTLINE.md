# RAG Service Implementation Outline

## 🎯 Goal
Transform the basic RAG service into a full-featured document management system with:
- Hierarchical collections/folders
- Real-time document processing progress
- File upload support (not just text)
- MCP tool integration for AI search

## 📋 Current State Analysis

### What Exists:
- Basic text document upload (`POST /rag/documents`)
- Simple document processing with Celery
- Basic vector search
- Weaviate integration

### What's Missing:
- Collection/folder hierarchy
- File upload support
- Progress streaming
- User-specific document isolation
- MCP search integration

## 🏗️ Implementation Phases

### Phase 1: Collection Infrastructure (Week 1)

#### 1.1 Database Schema
```sql
-- Collections table (hierarchical structure)
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    collection_type VARCHAR(50) DEFAULT 'folder',
    icon VARCHAR(50) DEFAULT '📁',
    color VARCHAR(7) DEFAULT '#3B82F6',
    path VARCHAR(1024) NOT NULL,
    depth INTEGER NOT NULL DEFAULT 0,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    UNIQUE(user_id, parent_id, name)
);

-- Update existing tables
ALTER TABLE documents 
ADD COLUMN collection_id UUID REFERENCES collections(id),
ADD COLUMN user_id INTEGER REFERENCES users(id),
ADD COLUMN file_name VARCHAR(255),
ADD COLUMN file_size INTEGER,
ADD COLUMN mime_type VARCHAR(100),
ADD COLUMN processing_progress JSONB DEFAULT '{}';

ALTER TABLE chunks
ADD COLUMN collection_id UUID REFERENCES collections(id);

-- Indexes
CREATE INDEX idx_collections_parent ON collections(parent_id);
CREATE INDEX idx_collections_path ON collections(path);
CREATE INDEX idx_documents_collection ON documents(collection_id);
CREATE INDEX idx_chunks_collection ON chunks(collection_id);
```

#### 1.2 Domain Models
- Create `Collection` domain model
- Update `Document` model with collection support
- Add `ProcessingProgress` model

#### 1.3 Collection Repository
- CRUD operations for collections
- Path management (build full paths)
- Breadcrumb navigation support
- List children by parent

#### 1.4 API Endpoints
```
POST   /api/rag/collections                  # Create collection/folder
GET    /api/rag/collections                  # List root collections
GET    /api/rag/collections/{id}            # Get collection details
GET    /api/rag/collections/{id}/children   # List sub-folders
GET    /api/rag/collections/{id}/path       # Get breadcrumb path
PATCH  /api/rag/collections/{id}            # Update collection
DELETE /api/rag/collections/{id}            # Delete collection
POST   /api/rag/collections/{id}/move       # Move to different parent
```

### Phase 2: Document Upload & Processing (Week 2)

#### 2.1 File Upload Support
- Update document upload to accept files (not just text)
- Store files in local storage or S3
- Extract text from PDFs, DOCX, etc.
- Update endpoint: `POST /api/rag/collections/{id}/documents`

#### 2.2 Async Processing Pipeline
```python
@celery_app.task(bind=True)
def process_document_with_progress(self, document_id: str, collection_id: str):
    # Steps:
    # 1. Load document (10%)
    # 2. Extract text (20%)
    # 3. Split into chunks (30%)
    # 4. Generate embeddings (50-90%)
    # 5. Store in vector DB (95%)
    # 6. Complete (100%)
```

#### 2.3 Progress Tracking
- Redis pub/sub for real-time updates
- Progress structure:
  ```json
  {
    "document_id": "uuid",
    "status": "processing",
    "percentage": 45,
    "current_step": "Generating embeddings",
    "chunks_processed": 15,
    "total_chunks": 30,
    "error": null
  }
  ```

#### 2.4 SSE Streaming Endpoint
```python
GET /api/rag/documents/{id}/progress
# Returns Server-Sent Events stream
```

### Phase 3: Search & Retrieval (Week 3)

#### 3.1 Collection-Aware Search
- Filter searches by collection path
- Support recursive search in sub-folders
- Maintain collection context in results

#### 3.2 MCP Search Tool
```python
class RAGSearchTool:
    async def search_knowledge(
        query: str,
        collection_ids: List[str] = None,
        collection_paths: List[str] = None,
        include_subfolders: bool = True,
        max_results: int = 5
    )
```

#### 3.3 Enhanced Vector Search
- Namespace vectors by collection in Weaviate
- Add metadata filters for collection context
- Return results with full path context

### Phase 4: Integration & Polish (Week 4)

#### 4.1 Gateway Integration
- Add collection context to chat endpoints
- Support @ mentions with paths
- Pass collection filters to RAG service

#### 4.2 Frontend Components
- Collection browser tree view
- Document upload with progress bar
- @ mention autocomplete with paths

#### 4.3 Testing & Documentation
- Integration tests for full pipeline
- API documentation
- Usage examples

## 📊 Implementation Order

### Day 1-2: Database & Models
1. Create and run migration for collections table
2. Create Collection domain model
3. Create CollectionRepository with basic CRUD
4. Add collection endpoints to RAG router

### Day 3-4: File Upload
1. Update document upload to accept files
2. Add file storage service
3. Implement text extraction for PDFs
4. Update document model and repository

### Day 5-6: Async Processing
1. Create Celery task for document processing
2. Add progress tracking to Redis
3. Implement SSE endpoint for progress
4. Test end-to-end processing

### Day 7-8: Search Integration
1. Update vector store with collection namespacing
2. Implement collection-filtered search
3. Create MCP search tool
4. Test search functionality

### Day 9-10: Polish & Testing
1. Integration with gateway service
2. Error handling and edge cases
3. Performance optimization
4. Documentation

## 🚀 Quick Start Commands

```bash
# 1. Create migration
alembic revision -m "Add collections and update documents"

# 2. Apply migration
alembic upgrade head

# 3. Test collection creation
curl -X POST localhost:8000/api/rag/collections \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Legal Cases", "description": "Active legal cases"}'

# 4. Test document upload
curl -X POST localhost:8000/api/rag/collections/{id}/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf"

# 5. Watch progress
curl -N localhost:8000/api/rag/documents/{id}/progress
```

## 🎯 Success Criteria

1. **Collections Work**: Users can create nested folder structures
2. **Upload Works**: PDF/DOCX files can be uploaded and processed
3. **Progress Works**: Real-time progress updates during processing
4. **Search Works**: Documents can be found with collection context
5. **MCP Works**: AI can search specific collections via tools

## 📝 Key Files to Modify

1. `src/privategpt/services/rag/api/rag_router.py` - Add collection endpoints
2. `src/privategpt/core/domain/` - Add collection.py model
3. `src/privategpt/infra/database/models.py` - Update schema
4. `src/privategpt/infra/database/` - Add collection_repository.py
5. `src/privategpt/infra/tasks/` - Update Celery tasks
6. `src/privategpt/services/gateway/core/mcp_client.py` - Add search tool

Ready to start with Phase 1: Creating the database schema!