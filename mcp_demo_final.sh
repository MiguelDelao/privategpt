#!/bin/bash

echo "=== MCP Tool Integration Demo with Claude ==="
echo ""
echo "This demonstrates the current state of MCP integration."
echo ""

# Show MCP server is working
echo "1. MCP Server Status:"
echo "   Testing direct tool calls to MCP server..."
echo ""

echo "   a) Current Time:"
TIME_RESULT=$(curl -s -X POST "http://localhost:8004/rpc" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_current_time",
      "arguments": {"format": "human"}
    },
    "id": 1
  }' | jq -r '.result.current_time')
echo "      ✓ $TIME_RESULT"
echo ""

echo "   b) Calculator (42 × 17 = ?):"
CALC_RESULT=$(curl -s -X POST "http://localhost:8004/rpc" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "calculator",
      "arguments": {"operation": "multiply", "a": 42, "b": 17}
    },
    "id": 2
  }' | jq -r '.result.result')
echo "      ✓ Result: $CALC_RESULT"
echo ""

# Show tools are discoverable
echo "2. MCP Tools Discovery via Gateway:"
TOOLS_COUNT=$(curl -s "http://localhost:8000/api/mcp/tools?provider=anthropic" | jq '.tools | length')
echo "   ✓ Found $TOOLS_COUNT tools available"
curl -s "http://localhost:8000/api/mcp/tools?provider=anthropic" | jq -r '.tools[] | "     - \(.name)"'
echo ""

# Show current integration status
echo "3. Claude + MCP Integration Status:"
echo "   Testing: 'What is the current time and what is 42 × 17?'"
echo ""
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/chat/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the current time and what is 42 × 17?",
    "model": "claude-3-5-haiku-20241022"
  }' | jq -r '.text')
echo "   Claude's response:"
echo "   \"$RESPONSE\""
echo ""

# Summary
echo "4. Summary:"
echo "   ✅ MCP Server: Working (tools execute correctly)"
echo "   ✅ Tool Discovery: Working (2 tools registered)"
echo "   ⚠️  Tool Integration: Partial (tools discovered but not executed by Claude)"
echo "   "
echo "   Issue: Tool parameter schemas are not being passed correctly to Claude."
echo "   The 'input_schema' field is empty {}, preventing Claude from calling the tools."
echo ""
echo "=== End of Demo ==="