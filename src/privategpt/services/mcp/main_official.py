#!/usr/bin/env python3
"""
PrivateGPT MCP Server - Official MCP SDK Version

Simple MCP server with calculator and time tools for testing.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
server = Server("PrivateGPT")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="calculator",
            description="Perform basic mathematical operations",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide", "power"],
                        "description": "The operation to perform"
                    },
                    "a": {
                        "type": "number",
                        "description": "First number"
                    },
                    "b": {
                        "type": "number", 
                        "description": "Second number"
                    }
                },
                "required": ["operation", "a", "b"]
            }
        ),
        Tool(
            name="get_current_time", 
            description="Get the current date and time",
            inputSchema={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone name (e.g., 'UTC', 'US/Eastern')",
                        "default": None
                    },
                    "format": {
                        "type": "string",
                        "enum": ["iso", "human", "unix"],
                        "description": "Output format",
                        "default": "iso"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "calculator":
        return await handle_calculator(arguments)
    elif name == "get_current_time":
        return await handle_get_time(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_calculator(args: dict) -> list[TextContent]:
    """Handle calculator tool."""
    try:
        operation = args["operation"]
        a = float(args["a"])
        b = float(args["b"])
        
        result = None
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "Division by zero",
                        "operation": operation,
                        "a": a,
                        "b": b
                    }, indent=2)
                )]
            result = a / b
        elif operation == "power":
            result = a ** b
        else:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Unknown operation: {operation}",
                    "valid_operations": ["add", "subtract", "multiply", "divide", "power"]
                }, indent=2)
            )]
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "operation": operation,
                "a": a,
                "b": b,
                "result": result,
                "expression": f"{a} {operation} {b} = {result}"
            }, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Calculator error: {e}")
        return [TextContent(
            type="text", 
            text=json.dumps({
                "error": f"Calculation failed: {str(e)}",
                "operation": args.get("operation"),
                "a": args.get("a"),
                "b": args.get("b")
            }, indent=2)
        )]


async def handle_get_time(args: dict) -> list[TextContent]:
    """Handle get current time tool."""
    try:
        timezone = args.get("timezone")
        format_type = args.get("format", "iso")
        
        # Get current time
        if timezone:
            try:
                from zoneinfo import ZoneInfo
                tz = ZoneInfo(timezone)
                now = datetime.now(tz)
            except Exception:
                # Fallback to UTC if timezone is invalid
                from zoneinfo import ZoneInfo
                now = datetime.now(ZoneInfo("UTC"))
                timezone = "UTC (fallback - invalid timezone provided)"
        else:
            now = datetime.now()
            timezone = "local"
        
        # Format the time
        if format_type == "iso":
            time_str = now.isoformat()
        elif format_type == "human":
            time_str = now.strftime("%A, %B %d, %Y at %I:%M:%S %p")
        elif format_type == "unix":
            import time
            time_str = str(int(time.mktime(now.timetuple())))
        else:
            time_str = now.isoformat()
            format_type = "iso (default)"
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "current_time": time_str,
                "timezone": timezone,
                "format": format_type,
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "second": now.second,
                "weekday": now.strftime("%A"),
                "iso_time": now.isoformat()
            }, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Time retrieval error: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Failed to get time: {str(e)}",
                "timezone": args.get("timezone"),
                "format": args.get("format")
            }, indent=2)
        )]


async def main():
    """Main entry point."""
    logger.info("Starting PrivateGPT MCP Server (Official SDK)...")
    
    # Run server with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())