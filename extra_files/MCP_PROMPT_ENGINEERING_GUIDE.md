# MCP Prompt Engineering & Tool Integration Guide

## Current System Overview

### 1. Prompt Management System
You already have a **sophisticated prompt management system** with:
- Database-backed prompts (PostgreSQL)
- Model pattern matching (e.g., `privategpt-mcp`, `ollama:*`, `*mcp*`)
- XML-structured prompts with sections for persona, communication, tool_calling, etc.
- REST API for CRUD operations
- Admin-only endpoints for prompt management
- Test endpoint to try prompts before saving

### 2. API Endpoints for Prompt Management

```bash
# List all prompts (admin only)
GET /api/prompts/

# Get specific prompt
GET /api/prompts/{id}

# Create new prompt (admin only)
POST /api/prompts/
{
  "name": "my-mcp-prompt",
  "model_pattern": "privategpt-mcp",
  "prompt_xml": "<persona>...</persona>",
  "description": "Custom MCP prompt",
  "is_default": false
}

# Update prompt (admin only)
PATCH /api/prompts/{id}
{
  "prompt_xml": "<updated>...</updated>"
}

# Test prompt (admin only)
POST /api/prompts/test
{
  "prompt_xml": "<test>...</test>",
  "model_name": "privategpt-mcp",
  "test_message": "Hello, test this prompt"
}

# Get prompt for specific model
GET /api/prompts/for-model/{model_name}
```

### 3. How Tools are Defined

MCP tools are defined in `src/privategpt/services/mcp/main.py` using decorators:

```python
@mcp.tool()
async def search_documents(
    query: str,
    limit: int = 10,
    include_sources: bool = True
) -> str:
    """Search through uploaded documents using semantic similarity."""
    # Tool implementation
```

These tools are:
- `search_documents` - RAG search
- `rag_chat` - RAG-powered chat
- `create_file` - File creation
- `read_file` - File reading
- `edit_file` - File editing
- `list_directory` - Directory listing
- `get_system_info` - System information
- `check_service_health` - Service health check

## Tool Integration Architecture

### Current Flow (Not Yet Connected)
```
1. User Message → Gateway
2. Gateway adds system prompt from DB
3. Gateway → LLM Service (Ollama)
4. Ollama generates response (no tools yet)
```

### Target Flow with MCP
```
1. User Message → Gateway
2. Gateway loads XML prompt with tool instructions
3. Gateway → LLM Service
4. LLM Service connects to MCP server
5. LLM Service converts MCP tools to Ollama format
6. Ollama calls tools during generation
7. MCP executes tools (e.g., search_documents)
8. Results fed back to Ollama
9. Final response with tool results
```

## XML Prompt Engineering Strategy

### 1. Base Structure
```xml
<system>
<!-- Persona defines the AI's character and capabilities -->
<persona>
You are PrivateGPT, a local AI assistant with powerful document search and file management capabilities through MCP tools.
</persona>

<!-- Communication style and guidelines -->
<communication>
- Be concise and direct
- Explain tool usage clearly
- Show progress for long operations
</communication>

<!-- Tool calling instructions - CRITICAL SECTION -->
<tool_calling>
You have access to these tools:
- search_documents(query, limit): Search uploaded documents
- rag_chat(question): Get comprehensive answers from documents
- read_file(path): Read local files
- create_file(path, content): Create new files
- list_directory(path): Browse directories

IMPORTANT: Always use search_documents BEFORE answering questions about user content.
</tool_calling>

<!-- UI rendering tags for the frontend -->
<ui_rendering>
- <thinking>Internal reasoning</thinking>
- <status>Operation progress</status>
- <error>Error messages</error>
- <warning>Important notices</warning>
</ui_rendering>
</system>
```

### 2. Tool Instruction Patterns

For effective tool usage, you need clear XML patterns:

```xml
<tool_instructions>
<!-- Pattern 1: Mandatory tool usage -->
<rule priority="high">
WHEN user asks about uploaded documents
THEN MUST use search_documents first
NEVER answer from general knowledge
</rule>

<!-- Pattern 2: Tool chaining -->
<rule priority="medium">
WHEN search_documents returns results
AND user needs comprehensive answer
THEN use rag_chat with the question
</rule>

<!-- Pattern 3: Error handling -->
<rule priority="high">
WHEN tool returns error
THEN explain error clearly
AND suggest alternative approach
</rule>
</tool_instructions>
```

### 3. Model-Specific Prompts

Create different prompts for different scenarios:

```python
# For MCP-enabled models
model_pattern: "privategpt-mcp"
prompt_xml: "<system>...</system>"  # Full tool instructions

# For models without MCP
model_pattern: "ollama:llama3*"
prompt_xml: "<simple>...</simple>"  # No tool references

# For testing/debugging
model_pattern: "*debug*"
prompt_xml: "<debug>Show all thinking...</debug>"
```

## Practical Prompt Engineering Workflow

### Step 1: Create Base MCP Prompt
```bash
curl -X POST http://localhost:8000/api/prompts/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mcp-base",
    "model_pattern": "privategpt-mcp",
    "prompt_xml": "<system>...</system>",
    "description": "Base MCP prompt with tools",
    "is_default": false
  }'
```

### Step 2: Test Variations
```bash
# Test search-focused prompt
curl -X POST http://localhost:8000/api/prompts/test \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "prompt_xml": "<system><tool_calling>ALWAYS search first...</tool_calling></system>",
    "model_name": "privategpt-mcp",
    "test_message": "What documents do you have about AI?"
  }'
```

### Step 3: A/B Testing Strategy
Create multiple prompts with different patterns:

1. **Aggressive Tool Usage**
```xml
<tool_calling>
You MUST use tools for EVERY request.
Never answer without searching first.
</tool_calling>
```

2. **Balanced Approach**
```xml
<tool_calling>
Use tools when relevant.
For document questions, always search.
For general questions, use your knowledge.
</tool_calling>
```

3. **Minimal Tool Usage**
```xml
<tool_calling>
Tools are available if needed.
Prefer direct answers when possible.
</tool_calling>
```

### Step 4: Monitor and Iterate
Track which prompts work best for:
- Search accuracy
- Tool usage efficiency
- User satisfaction
- Response time

## Implementation Recommendations

### 1. Quick Testing Setup
Create a test script to rapidly iterate on prompts:

```python
# test_prompts.py
import httpx
import asyncio

async def test_prompt_variation(prompt_xml, test_query):
    async with httpx.AsyncClient() as client:
        # Test the prompt
        response = await client.post(
            "http://localhost:8000/api/prompts/test",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={
                "prompt_xml": prompt_xml,
                "model_name": "privategpt-mcp",
                "test_message": test_query
            }
        )
        return response.json()

# Test different variations
prompts = [
    "<system><tool_calling>ALWAYS search...</tool_calling></system>",
    "<system><tool_calling>Search when needed...</tool_calling></system>",
]

for prompt in prompts:
    result = await test_prompt_variation(prompt, "Tell me about the documents")
    print(f"Result: {result}")
```

### 2. Prompt Version Control
Since prompts are critical, consider:
- Exporting prompts to Git
- Version tracking in database
- Rollback capability
- A/B testing infrastructure

### 3. Tool Declaration Format
When Ollama supports function calling, tools will be declared like:

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "search_documents",
        "description": "Search through uploaded documents",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 10}
          },
          "required": ["query"]
        }
      }
    }
  ]
}
```

### 4. Dynamic Tool Selection
You asked about different tools for different scenarios. Options:

1. **Prompt-Based Selection**
```xml
<available_tools context="documents">
search_documents, rag_chat
</available_tools>

<available_tools context="files">
read_file, create_file, edit_file
</available_tools>
```

2. **User Preference**
```python
# In conversation metadata
{
  "enabled_tools": ["search_documents", "read_file"],
  "disabled_tools": ["create_file", "edit_file"]
}
```

3. **Model-Based**
```python
# Different tool sets for different models
TOOL_SETS = {
  "privategpt-mcp": ["all"],
  "privategpt-mcp-readonly": ["search_documents", "read_file"],
  "privategpt-mcp-search": ["search_documents", "rag_chat"]
}
```

## Next Steps

1. **Implement the missing /rag/search endpoint** (2 hours)
   - This unblocks MCP tool testing

2. **Create prompt variations** (4 hours)
   - Test different XML structures
   - Find optimal tool-calling patterns

3. **Build testing infrastructure** (2 hours)
   - Automated prompt testing
   - Performance metrics
   - User feedback collection

4. **Implement tool filtering** (4 hours)
   - Dynamic tool selection
   - User preferences
   - Context-aware tools

## Key Insights

1. **You already have the infrastructure** - The prompt management system is ready
2. **Tools are defined in code** - MCP server has all tools implemented
3. **Missing link is LLM integration** - Need to connect Ollama to MCP
4. **XML prompts are the control mechanism** - This is where you'll spend most time
5. **Testing is critical** - Use the /api/prompts/test endpoint extensively

Would you like me to:
1. Create specific XML prompt templates for different use cases?
2. Design a testing framework for prompt variations?
3. Implement the missing RAG search endpoint first?
4. Create a tool filtering system?