# MCP Integration Plan for PrivateGPT

## Executive Summary

This document outlines the production implementation plan for integrating Model Context Protocol (MCP) into PrivateGPT. MCP enables LLMs to use external tools (like document search, calculations, file operations) through a standardized protocol.

## Current State Analysis

### What We Have:
1. **MCP Server** (`mcp-service` on port 8004)
   - Implemented as a standalone FastMCP server
   - Contains tool definitions (calculator, time, document search, file operations)
   - Uses JSON-RPC protocol over stdio/HTTP
   - Currently isolated - no other services connect to it

2. **LLM Service** (`llm-service` on port 8003)
   - Handles text generation and chat
   - Multi-provider support (Ollama, OpenAI, Anthropic)
   - No awareness of MCP or tools
   - No tool-calling capabilities

3. **Gateway Service** (`gateway-service` on port 8000)
   - Manages conversations and routing
   - Has placeholder for MCP client (`core/mcp_client.py`)
   - Not currently using MCP

### What We're Missing:
1. **MCP Client Library** - Protocol implementation for connecting to MCP servers
2. **Tool Discovery** - Mechanism for LLM to know what tools are available
3. **Tool Calling Logic** - Decision making about when/how to use tools
4. **Response Integration** - Combining tool results with LLM responses

## Architecture Decision: Where Should MCP Client Live?

### Option 1: In LLM Service (Not Recommended)
```
User → Gateway → LLM Service (with MCP Client) → MCP Server
                       ↓
                  Text Generation
```
**Pros:** Direct integration with model
**Cons:** Violates single responsibility, couples LLM with tools

### Option 2: In Gateway Service (Recommended) ✓
```
User → Gateway (orchestrates) → LLM Service (text generation)
           ↓                  ↘
      MCP Client              Tool results fed back to LLM
           ↓
      MCP Server
```
**Pros:** 
- Gateway already orchestrates conversations
- Can manage tool calls across multiple LLM requests
- Maintains service separation
- Easier to add tool approval/filtering

### Option 3: New Orchestration Service
```
User → Gateway → Orchestrator Service → LLM Service
                        ↓
                   MCP Client → MCP Server
```
**Pros:** Clean separation
**Cons:** Another service to maintain, increased complexity

**Decision: Option 2 - Implement MCP Client in Gateway Service**

## Implementation Plan

### Phase 1: MCP Client Implementation (Week 1)

#### 1.1 Create MCP Client Library
```python
# src/privategpt/shared/mcp_client/client.py
class MCPClient:
    """
    Implements MCP protocol specification
    - JSON-RPC 2.0 over stdio or HTTP transport
    - Tool discovery via 'tools/list' method
    - Tool execution via 'tools/call' method
    - Resource access via 'resources/read' method
    """
    
    async def connect(self, server_params: ServerParams)
    async def list_tools(self) -> List[Tool]
    async def call_tool(self, name: str, arguments: dict) -> ToolResult
    async def list_resources(self) -> List[Resource]
    async def read_resource(self, uri: str) -> ResourceContent
```

#### 1.2 Transport Layer
```python
# src/privategpt/shared/mcp_client/transports/
- stdio_transport.py  # For subprocess MCP servers
- http_transport.py   # For HTTP-based MCP servers
- websocket_transport.py  # For real-time connections
```

#### 1.3 Protocol Implementation
```python
# src/privategpt/shared/mcp_client/protocol.py
- JSON-RPC 2.0 message formatting
- Request/response correlation
- Error handling (protocol errors vs tool errors)
- Batch request support
```

### Phase 2: Gateway Integration (Week 1-2)

#### 2.1 Update Chat Service
```python
# src/privategpt/services/gateway/core/chat_service.py

class ChatService:
    def __init__(self):
        self.mcp_client = MCPClient()
        self.tool_registry = ToolRegistry()
    
    async def process_message_with_tools(self, message: str, conversation_id: str):
        # 1. Check if tools might be needed
        if self._should_consider_tools(message):
            # 2. Get available tools
            tools = await self.tool_registry.get_tools_for_context(conversation_id)
            
            # 3. Ask LLM if it wants to use tools
            tool_request = await self._get_tool_request(message, tools)
            
            # 4. Execute tools if requested
            if tool_request:
                results = await self._execute_tools(tool_request)
                
                # 5. Feed results back to LLM
                final_response = await self._generate_with_tool_results(
                    message, results
                )
```

#### 2.2 Tool Discovery & Registry
```python
# src/privategpt/services/gateway/core/tool_registry.py

class ToolRegistry:
    """
    Manages tool discovery and caching
    - Discovers tools from MCP servers on startup
    - Caches tool definitions
    - Provides tool schemas to LLM
    - Handles tool authorization per user/conversation
    """
    
    async def discover_all_tools(self)
    async def get_tool_schema(self, tool_name: str)
    async def validate_tool_access(self, user_id: str, tool_name: str)
```

### Phase 3: LLM Tool Calling (Week 2)

#### 3.1 Tool-Aware Prompting
```python
# System prompt additions for tool awareness
TOOL_SYSTEM_PROMPT = """
You have access to the following tools:

{tool_definitions}

To use a tool, respond with:
<tool_use>
{
  "tool": "tool_name",
  "arguments": {
    "arg1": "value1"
  }
}
</tool_use>

You may use multiple tools in sequence. After receiving tool results,
incorporate them naturally into your response.
"""
```

#### 3.2 Response Parser
```python
# src/privategpt/services/gateway/core/tool_parser.py

class ToolCallParser:
    """
    Parses LLM responses for tool calls
    - Supports multiple formats (XML, JSON, function-calling)
    - Validates tool calls against schemas
    - Handles malformed requests gracefully
    """
    
    def parse_response(self, llm_response: str) -> List[ToolCall]
    def validate_arguments(self, tool_call: ToolCall, schema: dict) -> bool
```

### Phase 4: Tool Execution Flow (Week 2-3)

#### 4.1 Execution Pipeline
```
1. User sends message
2. Gateway checks if tools might help
3. Gateway sends to LLM with tool definitions
4. LLM responds with text and/or tool calls
5. Gateway executes tool calls via MCP
6. Gateway sends tool results back to LLM
7. LLM generates final response
8. Gateway returns combined response to user
```

#### 4.2 State Management
```python
# Track tool usage in conversation
class ToolExecutionContext:
    conversation_id: str
    tools_used: List[ToolCall]
    tool_results: List[ToolResult]
    total_tool_time_ms: int
    
# Store in conversation metadata
conversation.metadata["tool_context"] = context
```

### Phase 5: Enhanced Tool Features (Week 3-4)

#### 5.1 Tool Approval System
```python
# For sensitive tools, require user approval
class ToolApprovalService:
    async def requires_approval(self, tool_name: str) -> bool
    async def request_approval(self, user_id: str, tool_call: ToolCall)
    async def check_approval_status(self, approval_id: str)
```

#### 5.2 Tool Result Rendering
```python
# Special rendering for different tool types
class ToolResultRenderer:
    def render_calculation(self, result: dict) -> str
    def render_search_results(self, results: list) -> str
    def render_file_operation(self, result: dict) -> str
    def render_error(self, error: dict) -> str
```

#### 5.3 Streaming with Tools
```python
# Support streaming responses even with tool calls
async def stream_with_tools(self, message: str):
    # Stream initial LLM response
    async for chunk in llm.stream(message):
        if self._detect_tool_call(chunk):
            # Pause streaming
            tool_result = await self._execute_tool(chunk)
            # Resume with tool result
            async for final_chunk in llm.stream_with_context(tool_result):
                yield final_chunk
        else:
            yield chunk
```

## Configuration & Deployment

### Environment Variables
```yaml
# Gateway service
MCP_ENABLED: "true"
MCP_SERVER_URL: "http://mcp-service:8000"
MCP_TIMEOUT_SECONDS: "30"
MCP_MAX_TOOL_CALLS: "10"  # Per conversation turn
MCP_TOOL_APPROVAL_REQUIRED: "false"  # Set true for production

# Tool-specific configs
MCP_ENABLE_FILE_TOOLS: "false"  # Security consideration
MCP_ENABLE_SYSTEM_TOOLS: "false"
MCP_SEARCH_TOOLS_ENABLED: "true"
```

### Docker Compose Updates
```yaml
gateway-service:
  depends_on:
    - mcp-service  # Add dependency
  environment:
    - MCP_ENABLED=true
    - MCP_SERVER_URL=http://mcp-service:8000
```

## Security Considerations

1. **Tool Authorization**
   - Implement per-user tool permissions
   - Audit trail for all tool usage
   - Rate limiting per tool/user

2. **Input Validation**
   - Validate all tool arguments against schemas
   - Sanitize file paths and system commands
   - Prevent injection attacks

3. **Result Filtering**
   - Filter sensitive information from tool results
   - Implement data access controls
   - Respect document permissions in search

## Testing Strategy

### Unit Tests
- MCP client protocol implementation
- Tool parser accuracy
- Tool registry functionality

### Integration Tests
- Full tool execution flow
- Error handling scenarios
- Streaming with tools

### E2E Tests
- User asks for calculation → gets result
- User searches documents → gets relevant results
- Multi-tool conversations

## Migration Path

1. **Phase 1**: Deploy with MCP disabled (MCP_ENABLED=false)
2. **Phase 2**: Enable for internal testing with limited tools
3. **Phase 3**: Gradual rollout with approval system
4. **Phase 4**: Full production with all tools enabled

## Success Metrics

1. **Tool Usage Rate**: % of conversations using tools
2. **Tool Success Rate**: % of tool calls completing successfully
3. **Response Quality**: User satisfaction with tool-augmented responses
4. **Performance**: Additional latency from tool calls (<500ms target)

## Timeline

- **Week 1**: MCP client implementation
- **Week 2**: Gateway integration and basic tool calling
- **Week 3**: Advanced features (approval, streaming)
- **Week 4**: Testing and optimization
- **Week 5**: Production deployment

## Next Steps

1. Review and approve this plan
2. Set up MCP client development environment
3. Begin Phase 1 implementation
4. Create test MCP server for development
5. Update API documentation with tool capabilities