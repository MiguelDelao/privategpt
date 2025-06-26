# MCP + Ollama Tool Integration Example

## How Tool Calling Works in LLMs

### 1. Tool Definition Format (OpenAI/Anthropic Style)
```json
{
  "model": "qwen2.5:3b",
  "messages": [
    {
      "role": "system",
      "content": "<system>You are an AI with access to document search...</system>"
    },
    {
      "role": "user", 
      "content": "What documents do you have about AI?"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "search_documents",
        "description": "Search through uploaded documents using semantic similarity",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "The search query"
            },
            "limit": {
              "type": "integer",
              "description": "Maximum number of results (default: 10)",
              "default": 10
            },
            "include_sources": {
              "type": "boolean",
              "description": "Whether to include source document information",
              "default": true
            }
          },
          "required": ["query"]
        }
      }
    }
  ]
}
```

### 2. LLM Response with Tool Call
```json
{
  "id": "msg_123",
  "model": "qwen2.5:3b",
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "call_456",
      "type": "function",
      "function": {
        "name": "search_documents",
        "arguments": "{\"query\": \"AI artificial intelligence\", \"limit\": 5}"
      }
    }
  ]
}
```

### 3. Tool Execution & Response
```json
{
  "role": "tool",
  "tool_call_id": "call_456",
  "content": "{\"results\": [{\"text\": \"AI is transforming...\", \"score\": 0.92}], \"total_found\": 5}"
}
```

### 4. Final LLM Response
```json
{
  "role": "assistant",
  "content": "Based on my search, I found 5 documents about AI. The most relevant discusses how AI is transforming industries..."
}
```

## Current Ollama Limitations & Workarounds

### Option 1: Prompt-Based Tool Calling (Current Approach)
```xml
<system>
<tool_instructions>
When you need to search documents, respond EXACTLY in this format:
TOOL_CALL: search_documents
QUERY: your search query here
END_TOOL_CALL

Wait for the result before continuing.
</tool_instructions>
</system>
```

Then parse the response:
```python
if "TOOL_CALL: search_documents" in response:
    # Extract query and execute tool
    query = extract_between("QUERY:", "END_TOOL_CALL", response)
    result = await mcp_client.execute_tool("search_documents", {"query": query})
    # Continue conversation with result
```

### Option 2: JSON Mode (If Supported)
Some Ollama models support JSON output:
```python
response = await ollama.chat(
    model="qwen2.5:3b",
    messages=messages,
    format="json",
    system_prompt="Respond with {\"action\": \"search\", \"query\": \"...\"} when searching"
)
```

### Option 3: Few-Shot Examples in Prompt
```xml
<examples>
User: What documents do you have?
Assistant: I'll search for available documents.
[Searching documents with query: "*"]
Based on the search results, you have documents about...

User: Tell me about AI
Assistant: I'll search for AI-related documents.
[Searching documents with query: "AI artificial intelligence"]
I found several documents about AI...
</examples>
```

## Recommended Implementation Path

### Phase 1: Structured Output Parsing (1 week)
```python
class ToolCallParser:
    def extract_tool_calls(self, response: str) -> List[ToolCall]:
        # Parse patterns like [TOOL: search_documents(query="AI")]
        pattern = r'\[TOOL: (\w+)\((.*?)\)\]'
        matches = re.findall(pattern, response)
        return [self.parse_tool_call(name, args) for name, args in matches]
```

### Phase 2: Ollama Function Calling (When Available)
Monitor Ollama releases for function calling support:
- Llama 3.2 has some support
- Qwen 2.5 may support it
- Mistral models often support tools

### Phase 3: Full Integration
```python
# Future implementation when Ollama supports tools
async def chat_with_mcp(messages, model="qwen2.5:3b"):
    # Get MCP tools
    tools = await mcp_client.list_tools()
    
    # Convert to Ollama format
    ollama_tools = convert_mcp_to_ollama_tools(tools)
    
    # Initial request
    response = await ollama.chat(
        model=model,
        messages=messages,
        tools=ollama_tools
    )
    
    # Handle tool calls
    if response.tool_calls:
        results = []
        for tool_call in response.tool_calls:
            result = await mcp_client.execute_tool(
                tool_call.function.name,
                json.loads(tool_call.function.arguments)
            )
            results.append(result)
        
        # Continue with results
        messages.append(response)
        messages.extend(format_tool_results(results))
        
        final_response = await ollama.chat(
            model=model,
            messages=messages
        )
        
        return final_response
    
    return response
```

## Testing Tool Integration Today

### 1. Manual Testing with Prompts
```bash
# Create a prompt that instructs structured output
curl -X POST http://localhost:8000/api/prompts/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "mcp-structured",
    "model_pattern": "privategpt-mcp",
    "prompt_xml": "<system><tool_format>Use [SEARCH: query] for searching...</tool_format></system>"
  }'
```

### 2. Mock Tool Responses
```python
# In your testing
MOCK_SEARCH_RESULT = {
    "chunks": [
        {"text": "AI is a rapidly growing field...", "score": 0.95},
        {"text": "Machine learning enables...", "score": 0.87}
    ]
}

# Test prompt handling of results
test_prompt = """
<system>
<search_result>
{json.dumps(MOCK_SEARCH_RESULT)}
</search_result>
Now answer: What is AI?
</system>
"""
```

### 3. Gradual Rollout
1. Start with search-only prompts
2. Add file operations once search works
3. Enable all tools for power users
4. Monitor usage patterns

## Key Decisions You Need to Make

1. **Tool Calling Format**
   - Structured text: `[TOOL: name(args)]`
   - JSON: `{"tool": "name", "args": {}}`
   - Natural language: "I'll search for X"

2. **Error Handling**
   - Retry failed tools automatically?
   - Fall back to general knowledge?
   - Always explain tool failures?

3. **Tool Permissions**
   - All tools for all users?
   - Role-based tool access?
   - Per-conversation tool settings?

4. **Prompt Strategy**
   - One master prompt with all tools?
   - Specialized prompts per use case?
   - Dynamic prompt construction?