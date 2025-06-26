#!/usr/bin/env python3
"""Debug MCP integration"""
import requests
import json

# First check if tools are available
print("1. Checking MCP tools availability...")
tools_response = requests.get("http://localhost:8000/api/mcp/tools?provider=anthropic")
tools = tools_response.json()
print(f"   Available tools: {len(tools['tools'])}")
for tool in tools['tools']:
    print(f"   - {tool['name']}: {tool.get('input_schema', 'NO SCHEMA!')}")
print()

# Check what the LLM service expects
print("2. Testing direct LLM call with tools...")
llm_payload = {
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "model": "claude-3-5-haiku-20241022",
    "tools": tools['tools']
}

# Try calling LLM service directly
try:
    llm_response = requests.post("http://llm-service:8000/chat", json=llm_payload, timeout=30)
    print(f"   LLM service response status: {llm_response.status_code}")
    if llm_response.status_code != 200:
        print(f"   Error: {llm_response.text}")
except Exception as e:
    print(f"   Failed to reach LLM service: {e}")

# Test via gateway
print("\n3. Testing via gateway MCP endpoint...")
mcp_response = requests.post("http://localhost:8000/api/chat/mcp", json={
    "message": "What is the current time and what is 15 times 23?",
    "model": "claude-3-5-haiku-20241022"
})
print(f"   Response: {mcp_response.json()}")