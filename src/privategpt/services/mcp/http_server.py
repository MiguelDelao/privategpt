#!/usr/bin/env python3
"""
HTTP wrapper for MCP Server - provides JSON-RPC 2.0 over HTTP

This creates an HTTP server that your gateway can connect to,
which internally uses the MCP protocol.
"""

import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

logger = logging.getLogger(__name__)

app = FastAPI(title="PrivateGPT MCP HTTP Server", version="1.0.0")

# Store for our MCP tools
AVAILABLE_TOOLS = {
    "calculator": {
        "name": "calculator",
        "description": "Perform basic mathematical operations",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide", "power"],
                    "description": "The operation to perform"
                },
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["operation", "a", "b"]
        }
    },
    "get_current_time": {
        "name": "get_current_time",
        "description": "Get the current date and time",
        "parameters": {
            "type": "object", 
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "Timezone name (optional)"
                },
                "format": {
                    "type": "string",
                    "enum": ["iso", "human", "unix"],
                    "description": "Output format",
                    "default": "iso"
                }
            }
        }
    }
}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mcp-http-server"}


@app.post("/rpc")
async def handle_jsonrpc(request: dict):
    """Handle JSON-RPC 2.0 requests."""
    try:
        # Validate JSON-RPC request
        if request.get("jsonrpc") != "2.0":
            raise HTTPException(status_code=400, detail="Invalid JSON-RPC version")
        
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        if method == "tools/list":
            # Return list of available tools
            result = {"tools": list(AVAILABLE_TOOLS.values())}
            
        elif method == "tools/call":
            # Execute a tool
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "calculator":
                result = await execute_calculator(arguments)
            elif tool_name == "get_current_time":
                result = await execute_get_time(arguments)
            else:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
                    "id": request_id
                })
        else:
            return JSONResponse({
                "jsonrpc": "2.0", 
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": request_id
            })
        
        return JSONResponse({
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        })
        
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": request.get("id")
        })


async def execute_calculator(args: dict) -> dict:
    """Execute calculator tool."""
    try:
        operation = args["operation"]
        a = float(args["a"])
        b = float(args["b"])
        
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Division by zero")
            result = a / b
        elif operation == "power":
            result = a ** b
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        return {
            "operation": operation,
            "a": a,
            "b": b,
            "result": result,
            "expression": f"{a} {operation} {b} = {result}"
        }
        
    except Exception as e:
        raise ValueError(f"Calculator error: {str(e)}")


async def execute_get_time(args: dict) -> dict:
    """Execute get time tool."""
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
                from zoneinfo import ZoneInfo
                now = datetime.now(ZoneInfo("UTC"))
                timezone = "UTC (fallback)"
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
        
        return {
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
        }
        
    except Exception as e:
        raise ValueError(f"Time error: {str(e)}")


if __name__ == "__main__":
    logger.info("Starting MCP HTTP Server on port 8000...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )