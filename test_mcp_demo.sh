#!/bin/bash

echo "=== MCP Tool Call Demonstration with Claude ==="
echo ""

# Get auth token
echo "1. Getting authentication token..."
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@admin.com", "password": "admin"}' | jq -r '.access_token')
echo "✓ Token obtained"
echo ""

# Show available MCP tools
echo "2. Available MCP Tools:"
curl -s "http://localhost:8000/api/mcp/tools?provider=anthropic" | jq '.tools[] | "  - \(.name): \(.description)"' -r
echo ""

# Test direct tool calls to MCP server
echo "3. Direct MCP Server Tool Calls:"
echo ""

echo "   a) Getting current time:"
curl -s -X POST "http://localhost:8004/rpc" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_current_time",
      "arguments": {"format": "human"}
    },
    "id": 1
  }' | jq '.result.current_time' -r
echo ""

echo "   b) Calculator (42 × 17):"
curl -s -X POST "http://localhost:8004/rpc" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "calculator",
      "arguments": {"operation": "multiply", "a": 42, "b": 17}
    },
    "id": 2
  }' | jq '.result.expression' -r
echo ""

# Test MCP-enabled chat endpoint
echo "4. Testing Claude with MCP Tools:"
echo "   Asking: 'What is the current time? Also, calculate 42 × 17 for me.'"
echo ""
echo "   Claude's response:"
curl -s -X POST "http://localhost:8000/api/chat/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the current time? Also, calculate 42 × 17 for me.",
    "model": "claude-3-5-haiku-20241022"
  }' | jq '.text' -r

echo ""
echo "=== Demo Complete ==="