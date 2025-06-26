# Complete MCP-RAG Integration Plan

## Architecture Overview

```
User → Gateway (/api/chat/mcp) → LLM Service → MCP Server → RAG Service
                                       ↓
                                  Ollama/OpenAI
                                  (with tools)
```

## Current Gaps

1. **RAG Service**: Missing `/rag/search` endpoint (MCP expects this)
2. **Gateway**: `/api/chat/mcp` endpoint not fully implemented
3. **LLM Service**: No MCP client integration
4. **Connection**: No actual tool execution flow

## Implementation Plan

### Phase 1: Create RAG Search Endpoint (2 hours)

**File**: `src/privategpt/services/rag/api/rag_router.py`

Add this endpoint:

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import time

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    include_metadata: bool = True

class SearchResponse(BaseModel):
    chunks: List[Dict[str, Any]]
    search_time_ms: int

@router.post("/search", response_model=SearchResponse)
async def search_documents(
    req: SearchRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Raw search endpoint for MCP tool integration."""
    start_time = time.time()
    
    # Use existing RAG service
    rag = build_rag_service(session)
    
    # Perform search
    search_results = await rag.search(SearchQuery(
        text=req.query,
        top_k=req.limit
    ))
    
    # Format chunks for MCP
    chunks = []
    for i, (chunk_id, score) in enumerate(search_results):
        chunks.append({
            "text": f"Search result {i+1} (score: {score:.2f})",
            "score": score,
            "chunk_id": chunk_id,
            "metadata": {
                "position": i,
                "source": "document"
            }
        })
    
    return SearchResponse(
        chunks=chunks,
        search_time_ms=int((time.time() - start_time) * 1000)
    )
```

### Phase 2: Implement MCP Client in LLM Service (4 hours)

**File**: `src/privategpt/services/llm/core/mcp_client.py`

```python
import asyncio
import json
from typing import Dict, List, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    """Client for communicating with MCP server."""
    
    def __init__(self, mcp_executable_path: str = "/app/mcp-server"):
        self.executable = mcp_executable_path
        self.session: Optional[ClientSession] = None
    
    async def connect(self):
        """Connect to MCP server via STDIO."""
        server_params = StdioServerParameters(
            command=self.executable,
            args=[],
            env={"RAG_SERVICE_URL": "http://rag-service:8000"}
        )
        
        self.session = await stdio_client(server_params)
        await self.session.__aenter__()
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get available tools from MCP server."""
        if not self.session:
            await self.connect()
        
        tools = await self.session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
            for tool in tools
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return result."""
        if not self.session:
            await self.connect()
        
        result = await self.session.call_tool(tool_name, arguments)
        return result.content[0].text if result.content else ""
    
    async def close(self):
        """Close MCP connection."""
        if self.session:
            await self.session.__aexit__(None, None, None)
```

### Phase 3: Update LLM Service Provider (3 hours)

**File**: `src/privategpt/services/llm/providers/ollama_provider.py`

Add MCP support:

```python
async def chat_with_tools(
    self,
    messages: List[Dict[str, str]],
    model: str,
    mcp_client: Optional[MCPClient] = None,
    **kwargs
) -> ChatResponse:
    """Chat with MCP tool support."""
    
    if not mcp_client:
        # Regular chat without tools
        return await self.chat(messages, model, **kwargs)
    
    # Get available tools
    tools = await mcp_client.list_tools()
    
    # Convert to Ollama tool format
    ollama_tools = []
    for tool in tools:
        if tool["name"] in ["search_documents", "rag_chat"]:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            })
    
    # Add tools to request
    response = await self.client.chat(
        model=model,
        messages=messages,
        tools=ollama_tools,
        **kwargs
    )
    
    # Handle tool calls
    if hasattr(response, 'message') and hasattr(response.message, 'tool_calls'):
        tool_results = []
        
        for tool_call in response.message.tool_calls:
            # Execute tool via MCP
            result = await mcp_client.execute_tool(
                tool_call.function.name,
                json.loads(tool_call.function.arguments)
            )
            
            tool_results.append({
                "tool_call_id": tool_call.id,
                "result": result
            })
        
        # Continue conversation with tool results
        messages.append(response.message)
        messages.append({
            "role": "tool",
            "content": json.dumps(tool_results)
        })
        
        # Get final response
        final_response = await self.client.chat(
            model=model,
            messages=messages,
            **kwargs
        )
        
        return self._format_response(final_response, tool_results=tool_results)
    
    return self._format_response(response)
```

### Phase 4: Complete Gateway Integration (2 hours)

**File**: `src/privategpt/services/gateway/api/chat_router.py`

Update the MCP endpoint:

```python
@router.post("/mcp", response_model=SimpleChatResponse)
async def mcp_chat(
    chat_request: SimpleChatRequest,
    db: AsyncSession = Depends(get_async_session_context)
):
    """Chat with MCP tool integration for RAG."""
    
    if not chat_request.use_mcp:
        return await direct_chat(chat_request)
    
    try:
        # Forward to LLM service with MCP flag
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{settings.LLM_SERVICE_URL}/chat/mcp",
                json={
                    "messages": [{"role": "user", "content": chat_request.message}],
                    "model": chat_request.model or "qwen2.5:3b",
                    "temperature": chat_request.temperature,
                    "max_tokens": chat_request.max_tokens,
                    "available_tools": chat_request.available_tools
                }
            )
            response.raise_for_status()
            
            result = response.json()
            
            return SimpleChatResponse(
                text=result["text"],
                model=result["model"],
                tools_used=result.get("tools_used", False),
                response_time_ms=result.get("response_time_ms")
            )
            
    except httpx.HTTPError as e:
        logger.error(f"MCP chat failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"MCP chat failed: {str(e)}"
        )
```

### Phase 5: Docker Configuration (1 hour)

Update `docker-compose.yml` to include MCP server:

```yaml
mcp-service:
  build:
    context: .
    dockerfile: docker/mcp/Dockerfile
  environment:
    RAG_SERVICE_URL: http://rag-service:8000
    LLM_SERVICE_URL: http://llm-service:8000
    GATEWAY_SERVICE_URL: http://gateway-service:8000
  command: python -m privategpt.services.mcp.main
  networks:
    - privategpt-network
```

### Phase 6: Testing Flow (2 hours)

1. **Test RAG Search Endpoint**:
```bash
curl -X POST http://localhost:8002/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "artificial intelligence", "limit": 5}'
```

2. **Test MCP Tool Directly**:
```bash
# Use MCP client to test search_documents tool
mcp-client call search_documents '{"query": "AI"}'
```

3. **Test End-to-End**:
```bash
curl -X POST http://localhost:8000/api/chat/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Search for information about artificial intelligence",
    "use_mcp": true,
    "model": "qwen2.5:3b"
  }'
```

## Implementation Order

1. **Day 1** (Quick Win):
   - Implement `/rag/search` endpoint with basic functionality
   - Test MCP server can call it successfully

2. **Day 2** (Core Integration):
   - Create MCP client in LLM service
   - Update Ollama provider with tool support
   - Test tool execution flow

3. **Day 3** (Complete Flow):
   - Finish gateway integration
   - Add proper error handling
   - End-to-end testing

## Key Decisions

1. **Tool Selection**: Only expose `search_documents` and `rag_chat` tools to LLM
2. **Authentication**: Internal services don't need auth (Docker network)
3. **Streaming**: Initial version won't support streaming with tools
4. **Models**: Start with Ollama models that support function calling (qwen2.5, llama3.2)

## Success Metrics

- [ ] RAG search endpoint returns chunks within 2 seconds
- [ ] MCP tool execution works reliably
- [ ] LLM can use search results to answer questions
- [ ] Error handling provides clear feedback
- [ ] System handles 10 concurrent requests

## Next Steps After Integration

1. Add collection filtering to search
2. Implement result ranking/reranking
3. Add caching for frequent queries
4. Support streaming responses with tool results
5. Add more sophisticated RAG tools (summarize, extract, etc.)