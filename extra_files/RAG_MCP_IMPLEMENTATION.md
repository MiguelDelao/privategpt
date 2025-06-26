# RAG MCP Integration - Implementation Guide

## Quick Summary
The MCP tool already exists. We just need to create the `/rag/search` endpoint it expects.

## Implementation Steps

### Step 1: Create Search Request/Response Models

**File**: `src/privategpt/services/rag/api/rag_router.py`

```python
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Max results")
    include_metadata: bool = Field(True, description="Include document metadata")
    collection_ids: Optional[List[str]] = Field(None, description="Filter by collections")

class ChunkResult(BaseModel):
    id: int
    text: str
    score: float
    document_id: int
    document_title: str
    collection_id: Optional[str]
    collection_name: Optional[str]
    position: int
    metadata: Dict[str, Any] = {}

class SearchResponse(BaseModel):
    chunks: List[ChunkResult]
    search_time_ms: int
    total_found: int
    query: str
```

### Step 2: Implement Search Endpoint

```python
@router.post("/search", response_model=SearchResponse)
async def search_documents(
    req: SearchRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user)  # Add when auth is ready
):
    """Raw semantic search endpoint for MCP integration."""
    
    start_time = time.time()
    
    # Build the RAG service
    rag = build_rag_service(session)
    
    # Create search query
    search_query = SearchQuery(
        text=req.query,
        top_k=req.limit,
        filters={"collection_ids": req.collection_ids} if req.collection_ids else None
    )
    
    # Perform vector search
    search_results = await rag.search(search_query)
    
    # Get chunk details with metadata
    chunk_results = []
    for chunk_id, score in search_results:
        # For now, we need to handle the UUID issue
        # TODO: Implement proper chunk retrieval by UUID
        
        # Temporary: Create mock result
        chunk_results.append(ChunkResult(
            id=1,  # Placeholder
            text="Chunk content here...",
            score=score,
            document_id=1,
            document_title="Document Title",
            collection_id=None,
            collection_name=None,
            position=0,
            metadata={}
        ))
    
    search_time = int((time.time() - start_time) * 1000)
    
    return SearchResponse(
        chunks=chunk_results,
        search_time_ms=search_time,
        total_found=len(chunk_results),
        query=req.query
    )
```

### Step 3: Fix Chunk Retrieval

We need to properly retrieve chunks by their UUIDs from Weaviate:

```python
async def get_chunks_by_uuids(
    self, 
    uuid_score_pairs: List[Tuple[str, float]], 
    session: AsyncSession
) -> List[ChunkResult]:
    """Retrieve chunk details from UUIDs returned by vector search."""
    
    results = []
    
    for uuid_str, score in uuid_score_pairs:
        # Query Weaviate for the chunk data
        client = await self.vector_store._ensure_client()
        
        # Get chunk from Weaviate by UUID
        collection = client.collections.get("PrivateGPTChunks")
        obj = collection.query.get_by_id(uuid_str)
        
        if obj and obj.properties:
            # Parse metadata
            metadata = {}
            if obj.properties.get("metadata"):
                try:
                    metadata = json.loads(obj.properties["metadata"])
                except:
                    pass
            
            # Get document and collection info from database
            doc_id = metadata.get("document_id")
            position = metadata.get("position", 0)
            
            if doc_id:
                # Query document and collection info
                doc = await session.get(DocumentModel, doc_id)
                collection = None
                if doc and doc.collection_id:
                    collection = await session.get(CollectionModel, doc.collection_id)
                
                results.append(ChunkResult(
                    id=position,  # Use position as ID for now
                    text=obj.properties.get("text", ""),
                    score=score,
                    document_id=doc_id,
                    document_title=doc.title if doc else "Unknown",
                    collection_id=doc.collection_id if doc else None,
                    collection_name=collection.name if collection else None,
                    position=position,
                    metadata=metadata
                ))
    
    return results
```

### Step 4: Update RagService

Add a method to get chunks with full metadata:

```python
# In src/privategpt/services/rag/core/service.py

async def search_with_metadata(self, query: SearchQuery) -> List[Tuple[str, float, Dict]]:
    """Search and return chunks with full metadata."""
    # Get embeddings
    emb = await self.embedder.embed_query(query.text)
    
    # Search vector store
    results = await self.vector_store.similarity_search(
        emb, 
        top_k=query.top_k, 
        filters=query.filters
    )
    
    # Results are (uuid, score) tuples
    # We need to fetch the actual chunk data
    
    enhanced_results = []
    for uuid_str, score in results:
        # This is where we'd retrieve chunk metadata
        # For now, return UUID and score with empty metadata
        enhanced_results.append((uuid_str, score, {}))
    
    return enhanced_results
```

### Step 5: Testing Script

Create a test script to verify the integration:

```bash
#!/bin/bash
# test_mcp_search.sh

echo "Testing MCP Search Integration"
echo "=============================="

# 1. Upload a test document
echo -e "\n1️⃣ Creating test collection..."
COLL=$(curl -s -X POST http://localhost:8002/rag/collections \
  -H "Content-Type: application/json" \
  -d '{"name": "MCP Test Collection", "icon": "🔍"}')

COLL_ID=$(echo "$COLL" | jq -r '.id')

echo -e "\n2️⃣ Uploading test document..."
DOC=$(curl -s -X POST "http://localhost:8002/rag/collections/$COLL_ID/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI Research Paper",
    "text": "This paper discusses the latest advances in artificial intelligence, including large language models, neural networks, and machine learning algorithms."
  }')

TASK_ID=$(echo "$DOC" | jq -r '.task_id')

# Wait for processing
echo -e "\n3️⃣ Waiting for processing..."
sleep 5

# 2. Test search endpoint directly
echo -e "\n4️⃣ Testing RAG search endpoint..."
SEARCH=$(curl -s -X POST http://localhost:8002/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence",
    "limit": 5,
    "include_metadata": true
  }')

echo "Search Response:"
echo "$SEARCH" | jq '.'

# 3. Test through MCP
echo -e "\n5️⃣ Testing through MCP tool..."
# This would require MCP client setup

# Cleanup
curl -s -X DELETE "http://localhost:8002/rag/collections/$COLL_ID?hard_delete=true"
```

## Implementation Priority

1. **First**: Create the `/rag/search` endpoint with mock data
2. **Second**: Test MCP tool can call the endpoint successfully  
3. **Third**: Implement proper chunk retrieval from Weaviate
4. **Fourth**: Add collection filtering support
5. **Fifth**: Optimize performance and add caching

## Quick Win Implementation

For immediate testing, implement a minimal search endpoint:

```python
@router.post("/search")
async def search_documents(req: dict, session: AsyncSession = Depends(get_async_session)):
    """Minimal search endpoint for MCP."""
    
    # Use existing chat logic but return chunks
    rag = build_rag_service(session)
    results = await rag.search(SearchQuery(text=req["query"], top_k=req.get("limit", 10)))
    
    # For now, return simple format
    return {
        "chunks": [
            {
                "text": f"Result {i+1} for query: {req['query']}",
                "score": score,
                "metadata": {"uuid": uuid}
            }
            for i, (uuid, score) in enumerate(results)
        ],
        "search_time_ms": 100,
        "query": req["query"]
    }
```

This will unblock MCP testing while we implement the full solution.