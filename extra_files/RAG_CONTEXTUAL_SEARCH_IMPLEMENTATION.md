# RAG Contextual Search Implementation

## Concept
Users can scope searches using `@` mentions:
- `@collection:reports` - Search only in "reports" collection
- `@document:annual-report-2024` - Search in specific document
- `@folder:financials` - Search in folder and subfolders
- `@tag:confidential` - Search documents with specific tag
- `@*` or no @ - Search everything

## Implementation Plan

### 1. Update MCP Tool Definition

**File**: `src/privategpt/services/mcp/main.py`

```python
@mcp.tool()
async def search_documents(
    query: str,
    context: Optional[str] = None,  # NEW: Add context parameter
    limit: int = 10,
    include_sources: bool = True
) -> str:
    """
    Search through uploaded documents using semantic similarity.
    
    Args:
        query: The search query
        context: Optional search context (e.g., "@collection:reports", "@document:doc-123")
        limit: Maximum number of results to return (default: 10)
        include_sources: Whether to include source document information
    
    Returns:
        JSON string with search results and sources
    """
    try:
        # Parse context if provided
        search_filters = {}
        if context:
            search_filters = parse_search_context(context)
        
        response = await http_client.post(
            f"{RAG_SERVICE_URL}/rag/search",
            json={
                "query": query,
                "limit": limit,
                "filters": search_filters,  # Pass parsed filters
                "include_metadata": include_sources
            }
        )
        response.raise_for_status()
        results = response.json()
        
        return json.dumps({
            "query": query,
            "context": context,
            "results": results.get("chunks", []),
            "total_found": len(results.get("chunks", [])),
            "search_time": results.get("search_time_ms", 0)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "query": query,
            "context": context
        }, indent=2)


def parse_search_context(context: str) -> Dict[str, Any]:
    """
    Parse context string into search filters.
    
    Examples:
        "@collection:reports" -> {"collection_name": "reports"}
        "@document:doc-123" -> {"document_id": "doc-123"}
        "@folder:financials" -> {"folder_path": "financials", "recursive": true}
        "@tag:confidential" -> {"tags": ["confidential"]}
    """
    if not context or not context.startswith("@"):
        return {}
    
    # Remove @ and split by :
    parts = context[1:].split(":", 1)
    if len(parts) != 2:
        return {}
    
    context_type, context_value = parts
    
    if context_type == "collection":
        return {"collection_name": context_value}
    elif context_type == "document":
        return {"document_id": context_value}
    elif context_type == "folder":
        return {"folder_path": context_value, "recursive": True}
    elif context_type == "tag":
        return {"tags": [context_value]}
    else:
        return {}
```

### 2. Update RAG Search Endpoint

**File**: `src/privategpt/services/rag/api/rag_router.py`

```python
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import time

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    limit: int = Field(10, ge=1, le=50, description="Maximum results")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    include_metadata: bool = Field(True, description="Include document metadata")

class ChunkResult(BaseModel):
    id: str
    text: str
    score: float
    document_id: int
    document_title: str
    collection_id: Optional[str]
    collection_name: Optional[str]
    position: int
    highlight: Optional[str] = None
    metadata: Dict[str, Any] = {}

class SearchResponse(BaseModel):
    chunks: List[ChunkResult]
    search_time_ms: int
    total_found: int
    query: str
    filters_applied: Dict[str, Any]


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    req: SearchRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user)  # When auth is ready
):
    """
    Raw semantic search endpoint for MCP integration.
    
    Supports filtering by:
    - collection_name: Search within a specific collection
    - collection_id: Search by collection UUID
    - document_id: Search within specific document
    - folder_path: Search within folder (with recursive option)
    - tags: Filter by document tags
    """
    start_time = time.time()
    
    # Build search filters
    search_filters = {}
    if req.filters:
        # Handle collection filtering
        if "collection_name" in req.filters:
            # Look up collection by name
            collection = await get_collection_by_name(
                session, 
                req.filters["collection_name"], 
                user.id
            )
            if collection:
                search_filters["collection_ids"] = [collection.id]
        
        elif "collection_id" in req.filters:
            search_filters["collection_ids"] = [req.filters["collection_id"]]
        
        # Handle document filtering
        if "document_id" in req.filters:
            search_filters["document_ids"] = [req.filters["document_id"]]
        
        # Handle folder filtering
        if "folder_path" in req.filters:
            # Get all collections in folder path
            collections = await get_collections_in_path(
                session,
                req.filters["folder_path"],
                user.id,
                recursive=req.filters.get("recursive", True)
            )
            if collections:
                search_filters["collection_ids"] = [c.id for c in collections]
    
    # Build RAG service
    rag = build_rag_service(session)
    
    # Create search query with filters
    search_query = SearchQuery(
        text=req.query,
        top_k=req.limit,
        filters=search_filters
    )
    
    # Perform search
    search_results = await rag.search(search_query)
    
    # Get detailed chunk information
    chunk_results = []
    for chunk_uuid, score in search_results:
        # Retrieve chunk details (this needs to be implemented properly)
        chunk_data = await get_chunk_details(session, chunk_uuid)
        
        if chunk_data:
            chunk_results.append(ChunkResult(
                id=chunk_uuid,
                text=chunk_data["text"],
                score=score,
                document_id=chunk_data["document_id"],
                document_title=chunk_data["document_title"],
                collection_id=chunk_data["collection_id"],
                collection_name=chunk_data["collection_name"],
                position=chunk_data["position"],
                highlight=highlight_query_in_text(req.query, chunk_data["text"]),
                metadata=chunk_data.get("metadata", {})
            ))
    
    search_time = int((time.time() - start_time) * 1000)
    
    return SearchResponse(
        chunks=chunk_results,
        search_time_ms=search_time,
        total_found=len(chunk_results),
        query=req.query,
        filters_applied=req.filters or {}
    )


async def get_collection_by_name(
    session: AsyncSession, 
    name: str, 
    user_id: int
) -> Optional[Collection]:
    """Get collection by name for user."""
    from privategpt.infra.database.collection_repository import CollectionRepository
    repo = CollectionRepository(session)
    collections = await repo.list_by_user(user_id)
    return next((c for c in collections if c.name.lower() == name.lower()), None)


async def get_collections_in_path(
    session: AsyncSession,
    path: str,
    user_id: int,
    recursive: bool = True
) -> List[Collection]:
    """Get all collections in a path."""
    from privategpt.infra.database.collection_repository import CollectionRepository
    repo = CollectionRepository(session)
    
    # This would need to be implemented in the repository
    # For now, return empty list
    return []


def highlight_query_in_text(query: str, text: str, context_chars: int = 50) -> str:
    """Highlight query terms in text with context."""
    # Simple implementation - can be enhanced
    query_lower = query.lower()
    text_lower = text.lower()
    
    pos = text_lower.find(query_lower)
    if pos >= 0:
        start = max(0, pos - context_chars)
        end = min(len(text), pos + len(query) + context_chars)
        
        highlighted = text[start:pos] + f"**{text[pos:pos+len(query)]}**" + text[pos+len(query):end]
        
        if start > 0:
            highlighted = "..." + highlighted
        if end < len(text):
            highlighted = highlighted + "..."
            
        return highlighted
    
    return text[:context_chars*2] + "..."
```

### 3. Update System Prompt

**File**: `mcp_contextual_search.xml`

```xml
<system>
<persona>
You are PrivateGPT, an intelligent AI assistant with powerful contextual document search capabilities.
</persona>

<context_search_instructions>
Users can scope their searches using @ mentions:
- @collection:name - Search only in the specified collection
- @document:id - Search within a specific document  
- @folder:path - Search in folder and all subfolders
- @tag:tagname - Search documents with specific tag
- No @ prefix - Search across all accessible documents

Examples:
- "Find revenue figures @collection:financial-reports"
- "What is the conclusion @document:thesis-2024"
- "Search for AI research @folder:papers/2024"
- "Find confidential data @tag:sensitive"

IMPORTANT: When users provide @context, you MUST pass it to the search_documents tool.
</context_search_instructions>

<tool_usage>
When calling search_documents with context:
1. Extract the @mention from the user's message
2. Pass it as the 'context' parameter
3. Keep the search query clean (remove the @mention from query)

Example:
User: "Find revenue data @collection:reports"
You call: search_documents(query="revenue data", context="@collection:reports")
</tool_usage>

<communication>
- Always acknowledge the search context when provided
- Explain if a context doesn't exist or has no results
- Suggest broader search if context is too narrow
</communication>

<thinking>
Before searching, analyze:
1. Is there an @context specified?
2. What is the core search query?
3. Should I search multiple contexts?
</thinking>
</system>
```

### 4. Enhanced Search Examples

```python
# User: "Find AI information @collection:research"
search_documents(
    query="AI information",
    context="@collection:research",
    limit=10
)

# User: "What are the financial results? @document:annual-report-2024"
search_documents(
    query="financial results",
    context="@document:annual-report-2024",
    limit=5
)

# User: "Search for neural networks @folder:papers/deep-learning"
search_documents(
    query="neural networks",
    context="@folder:papers/deep-learning",
    limit=20
)
```

### 5. Advanced Context Patterns

You could also support:

```python
# Multiple contexts
"@collection:reports,presentations"

# Exclusions
"@collection:* -@collection:drafts"

# Combined filters
"@folder:2024 @tag:published"

# Time-based
"@modified:last-week"
```

### 6. Implementation Priority

1. **Phase 1** (Simple):
   - Support `@collection:name` only
   - Basic string matching

2. **Phase 2** (Enhanced):
   - Add `@document:` and `@folder:`
   - Implement recursive folder search

3. **Phase 3** (Advanced):
   - Multiple contexts
   - Exclusions
   - Complex queries

## Testing the Context System

```bash
# Test collection search
curl -X POST http://localhost:8002/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "revenue data",
    "filters": {"collection_name": "financial-reports"},
    "limit": 10
  }'

# Test through MCP
# User message: "Find revenue @collection:financial-reports"
# MCP will parse and call with context
```

## Benefits

1. **User Control**: Users explicitly control search scope
2. **Performance**: Smaller search space = faster results
3. **Accuracy**: More relevant results from focused search
4. **Privacy**: Users can limit searches to specific areas
5. **Intuitive**: @ notation is familiar from social media