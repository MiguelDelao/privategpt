#!/usr/bin/env python3
"""
Test MCP streaming with Claude and tool calls
"""
import asyncio
import json
import httpx
from datetime import datetime

async def test_mcp_streaming():
    """Test MCP streaming with tool calls"""
    print("=== MCP Streaming Test with Claude ===\n")
    
    # Step 1: Login to get token
    print("1. Getting auth token...")
    async with httpx.AsyncClient() as client:
        login_response = await client.post(
            "http://localhost:8000/api/auth/login",
            json={"email": "admin@admin.com", "password": "admin"}
        )
        token = login_response.json()["access_token"]
        print(f"✓ Token obtained: {token[:20]}...\n")
    
    # Step 2: Test direct MCP chat (no streaming)
    print("2. Testing direct MCP chat with tools...")
    async with httpx.AsyncClient() as client:
        chat_response = await client.post(
            "http://localhost:8000/api/chat/mcp",
            json={
                "message": "What is the current time? Also, calculate 42 * 17 for me.",
                "model": "claude-3-5-haiku-20241022"
            }
        )
        result = chat_response.json()
        print(f"Response: {result['text']}")
        print(f"Tools used: {result['tools_used']}\n")
    
    # Step 3: Test MCP tools endpoint
    print("3. Checking available MCP tools...")
    async with httpx.AsyncClient() as client:
        tools_response = await client.get(
            "http://localhost:8000/api/mcp/tools?provider=anthropic"
        )
        tools_data = tools_response.json()
        print(f"Available tools: {len(tools_data['tools'])}")
        for tool in tools_data['tools']:
            print(f"  - {tool['name']}: {tool['description']}")
    
    # Step 4: Call MCP server directly
    print("\n4. Testing MCP server directly...")
    async with httpx.AsyncClient() as client:
        # Test get_current_time
        time_response = await client.post(
            "http://localhost:8004/rpc",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_current_time",
                    "arguments": {"format": "human"}
                },
                "id": 1
            }
        )
        time_result = time_response.json()
        print(f"Current time: {time_result['result']['current_time']}")
        
        # Test calculator
        calc_response = await client.post(
            "http://localhost:8004/rpc",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "calculator",
                    "arguments": {"operation": "multiply", "a": 42, "b": 17}
                },
                "id": 2
            }
        )
        calc_result = calc_response.json()
        print(f"Calculation: {calc_result['result']['expression']}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_mcp_streaming())