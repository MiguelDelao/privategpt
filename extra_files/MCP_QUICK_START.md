# MCP Integration Quick Start

## TL;DR

1. **You already have a prompt management system** - Use it via API
2. **MCP tools are already defined** - In `src/privategpt/services/mcp/main.py`
3. **Missing piece**: `/rag/search` endpoint (MCP expects it)
4. **Tool format**: Not in prompt, passed separately to LLM (when Ollama supports it)

## Immediate Actions

### 1. Get Your JWT Token
```bash
./get-jwt-token.sh
export JWT_TOKEN="your_token_here"
```

### 2. Create Sample Prompts
```bash
./manage_prompts.sh samples
# Creates mcp_basic.xml and mcp_advanced.xml
```

### 3. Test a Prompt
```bash
./manage_prompts.sh test mcp_basic.xml
```

### 4. Create Your MCP Prompt
```bash
./manage_prompts.sh create "my-mcp-prompt" "privategpt-mcp" mcp_advanced.xml
```

## How Tool Integration Actually Works

### Current Reality
```
User → Gateway → LLM (Ollama)
         ↓
    System Prompt (from DB)
```

### Target with MCP
```
User → Gateway → LLM (Ollama) ← Tool Definitions
         ↓              ↓
    System Prompt    MCP Server
```

### The Key Point
**Tools are NOT defined in the system prompt!** They are:
1. Defined in MCP server code (`@mcp.tool()` decorators)
2. Passed to LLM as a separate parameter (like OpenAI's `tools` param)
3. The prompt just tells the LLM HOW to use tools, not WHAT they are

## Your Prompt Engineering Focus

### What Goes in the Prompt
```xml
<system>
<!-- WHO the AI is -->
<persona>You are PrivateGPT with document search capabilities</persona>

<!-- HOW to use tools -->
<tool_instructions>
- Always search documents before answering
- Show what you're searching for
- Never make up document content
</tool_instructions>

<!-- WHEN to use tools -->
<decision_rules>
IF asked about documents → MUST search
IF asked about files → MAY use file tools
IF general question → answer directly
</decision_rules>

<!-- OUTPUT formatting -->
<formatting>
Use <thinking> for reasoning
Use [Searching: query] for transparency
</formatting>
</system>
```

### What Does NOT Go in the Prompt
- Tool definitions
- Parameter schemas
- Function signatures
- API endpoints

## Testing Workflow

### 1. Quick Test
```bash
# Test prompt directly
JWT_TOKEN=your_token ./manage_prompts.sh test mcp_basic.xml
```

### 2. Systematic Testing
```bash
# Run full test suite
python test_mcp_prompts.py --token YOUR_TOKEN
```

### 3. A/B Testing
```bash
# Create variations
./manage_prompts.sh create "mcp-aggressive" "*mcp*" mcp_aggressive.xml
./manage_prompts.sh create "mcp-balanced" "*mcp*" mcp_balanced.xml

# Test both
python test_mcp_prompts.py --token YOUR_TOKEN --prompt mcp-aggressive
python test_mcp_prompts.py --token YOUR_TOKEN --prompt mcp-balanced
```

## Implementing the Missing Piece

### Quick Fix for `/rag/search` (30 minutes)
```python
# In src/privategpt/services/rag/api/rag_router.py
@router.post("/search")
async def search_documents(req: dict, session = Depends(get_async_session)):
    """Quick implementation for MCP testing."""
    rag = build_rag_service(session)
    results = await rag.search(SearchQuery(text=req["query"], top_k=req.get("limit", 10)))
    
    return {
        "chunks": [
            {"text": f"Mock result {i+1}", "score": score}
            for i, (_, score) in enumerate(results)
        ],
        "search_time_ms": 100
    }
```

This unblocks MCP testing immediately!

## Decision Points

### 1. Prompt Strategy
- **Option A**: One master prompt with all instructions
- **Option B**: Specialized prompts per use case
- **Option C**: Dynamic prompt assembly

### 2. Tool Visibility
```xml
<!-- Explicit -->
<tools>search_documents, read_file, create_file</tools>

<!-- Implicit -->
<hint>You have document and file management capabilities</hint>

<!-- Hidden -->
<!-- No mention of tools, let behavior emerge -->
```

### 3. Error Handling
```xml
<!-- Graceful -->
<on_error>Explain issue and suggest alternatives</on_error>

<!-- Strict -->
<on_error>Stop and report exact error</on_error>
```

## Next Steps Priority

1. **NOW** (Today):
   - Implement `/rag/search` endpoint
   - Test existing MCP tools work
   
2. **SOON** (This Week):
   - Create 3-5 prompt variations
   - Run systematic tests
   - Pick winning prompt
   
3. **LATER** (Next Week):
   - Connect LLM to MCP properly
   - Implement tool filtering
   - Add streaming support