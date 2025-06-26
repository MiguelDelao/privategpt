#!/usr/bin/env python3
"""
PrivateGPT MCP Server - HTTP Version

Simple HTTP server that provides MCP-style tools for testing.
Just calculator and time tools for now.
"""

# Just import and run the HTTP server
from privategpt.services.mcp.http_server import app
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting PrivateGPT MCP HTTP Server on port 8000...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )