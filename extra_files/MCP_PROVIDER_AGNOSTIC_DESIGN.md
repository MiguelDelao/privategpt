# MCP Provider-Agnostic Design

## The Problem with the Old Implementation

The old `mcp_client.py` was hardcoded for Ollama:
- `format_tools_for_ollama()` - Only worked with Ollama's format
- `process_tool_calls()` - Expected Ollama-specific tool call structure  
- Defeated the purpose of having a multi-provider LLM system

## The New Provider-Agnostic Design

### Key Principles:

1. **Provider Independence**: The MCP client doesn't know or care which LLM provider is being used
2. **Standardized Format**: Tools are provided in a standardized format that any provider can adapt
3. **Adapter Pattern**: Each LLM provider adapter handles its own tool format conversion

### How It Works:

```python
# 1. MCP Client provides standardized tool format
tools = mcp_client.get_tools_for_llm(user_role="user", model_provider="openai")
# Returns:
[{
    "name": "calculator",
    "description": "Perform calculations",
    "parameters": { /* JSON Schema */ },
    "requires_approval": false,
    "auto_approved": true
}]

# 2. Each provider adapter transforms as needed
# In OpenAI adapter:
def format_tools_for_openai(tools):
    return [{
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"]
        }
    }]

# In Anthropic adapter:
def format_tools_for_anthropic(tools):
    return [{
        "name": tool["name"],
        "description": tool["description"],
        "input_schema": tool["parameters"]
    }]

# In Ollama adapter:
def format_tools_for_ollama(tools):
    # Ollama-specific format
    ...
```

### Integration Flow:

```
User Message
    ↓
Gateway Service
    ↓
Chat Service checks if tools needed
    ↓
Get tools from MCP Client (standardized format)
    ↓
Send to LLM Service with model name
    ↓
Model Registry routes to correct provider
    ↓
Provider Adapter formats tools for its API
    ↓
LLM generates response with tool calls
    ↓
Gateway executes tools via MCP Client
    ↓
Results back to LLM for final response
```

### Benefits:

1. **Future Proof**: Add new LLM providers without changing MCP client
2. **Clean Separation**: MCP client focuses on tool management, not LLM specifics
3. **Flexibility**: Each provider can optimize its tool calling format
4. **Consistency**: Same tool behavior regardless of LLM provider

### Example: Adding a New Provider

To add support for a new LLM provider (e.g., Cohere):

1. Create `cohere_adapter.py` in LLM service
2. Implement tool format conversion:
   ```python
   def format_tools(self, standardized_tools):
       # Convert to Cohere's format
       return [...]
   ```
3. That's it! MCP client doesn't need any changes

### Tool Calling Format Examples:

**OpenAI Format:**
```json
{
  "type": "function",
  "function": {
    "name": "get_current_time",
    "parameters": { "type": "object", "properties": {...} }
  }
}
```

**Anthropic Format:**
```json
{
  "name": "get_current_time",
  "description": "Get current time",
  "input_schema": { "type": "object", "properties": {...} }
}
```

**Ollama Format:**
```json
{
  "type": "function",
  "function": {
    "name": "get_current_time",
    "description": "Get current time",
    "parameters": { "type": "object", "properties": {...} }
  }
}
```

The MCP client provides a standardized format, and each adapter transforms it appropriately.