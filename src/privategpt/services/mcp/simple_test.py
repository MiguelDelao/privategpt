#!/usr/bin/env python3
"""
Simple MCP server test - just to verify the MCP SDK works
"""

import asyncio
import json
import logging
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# Create MCP server
server = Server("SimpleTest")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_time",
            description="Get current time",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "get_time":
        now = datetime.now()
        return [TextContent(
            type="text",
            text=f"Current time: {now.isoformat()}"
        )]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    logger.info("Starting Simple MCP Test Server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())