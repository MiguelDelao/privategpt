from __future__ import annotations

"""
MCP Client for connecting Ollama to our MCP server tools.

This client embeds in the gateway service and translates between:
- Ollama's function calling format
- MCP (Model Context Protocol) tool invocations
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncIterator
import subprocess
import os

from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Base exception for MCP client errors"""
    pass


class MCPClient:
    """
    MCP client for connecting to local MCP server via stdio.
    
    Handles communication between Ollama and our MCP server tools.
    """
    
    def __init__(self, 
                 server_command: Optional[List[str]] = None,
                 server_env: Optional[Dict[str, str]] = None):
        self.server_command = server_command or [
            "python", "-m", "privategpt.services.mcp.main"
        ]
        self.server_env = server_env or {
            "RAG_SERVICE_URL": settings.rag_service_url,
            "LLM_SERVICE_URL": settings.llm_service_url,
            "GATEWAY_SERVICE_URL": "http://localhost:8000"
        }
        
        self.process: Optional[subprocess.Popen] = None
        self.available_tools: Dict[str, Dict[str, Any]] = {}
        self.is_initialized = False
        self._message_id = 0
    
    async def initialize(self) -> None:
        """Initialize MCP connection and discover available tools"""
        if self.is_initialized:
            return
        
        try:
            # Start MCP server process
            env = {**os.environ, **self.server_env}
            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Initialize MCP protocol
            await self._send_initialize()
            
            # Discover available tools
            await self._list_tools()
            
            self.is_initialized = True
            logger.info(f"MCP client initialized with {len(self.available_tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            await self.close()
            raise MCPClientError(f"MCP client initialization failed: {e}")
    
    async def _send_message(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send JSON-RPC message to MCP server"""
        if not self.process:
            raise MCPClientError("MCP server not started")
        
        self._message_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": self._message_id,
            "method": method,
            "params": params or {}
        }
        
        try:
            # Send message
            message_json = json.dumps(message) + '\n'
            self.process.stdin.write(message_json)
            self.process.stdin.flush()
            
            # Read response
            response_line = self.process.stdout.readline()
            if not response_line:
                raise MCPClientError("No response from MCP server")
            
            response = json.loads(response_line.strip())
            
            if "error" in response:
                raise MCPClientError(f"MCP server error: {response['error']}")
            
            return response.get("result", {})
            
        except json.JSONDecodeError as e:
            raise MCPClientError(f"Invalid JSON response: {e}")
        except Exception as e:
            raise MCPClientError(f"Communication error: {e}")
    
    async def _send_initialize(self) -> None:
        """Send initialize message to MCP server"""
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {}
            },
            "clientInfo": {
                "name": "privategpt-gateway",
                "version": "1.0.0"
            }
        }
        
        result = await self._send_message("initialize", params)
        logger.debug(f"MCP server initialized: {result}")
    
    async def _list_tools(self) -> None:
        """Discover available tools from MCP server"""
        result = await self._send_message("tools/list")
        
        tools = result.get("tools", [])
        self.available_tools = {}
        
        for tool in tools:
            tool_name = tool.get("name")
            if tool_name:
                self.available_tools[tool_name] = {
                    "name": tool_name,
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("inputSchema", {})
                }
        
        logger.info(f"Discovered MCP tools: {list(self.available_tools.keys())}")
    
    async def call_tool(self, 
                       tool_name: str, 
                       arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool and return the result.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        if not self.is_initialized:
            await self.initialize()
        
        if tool_name not in self.available_tools:
            raise MCPClientError(f"Tool '{tool_name}' not available")
        
        try:
            start_time = datetime.utcnow()
            
            params = {
                "name": tool_name,
                "arguments": arguments
            }
            
            result = await self._send_message("tools/call", params)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Extract content from MCP response
            content = ""
            if "content" in result:
                for item in result["content"]:
                    if item.get("type") == "text":
                        content += item.get("text", "")
            
            return {
                "success": True,
                "result": content,
                "execution_time_ms": int(execution_time),
                "tool_name": tool_name,
                "raw_result": result
            }
            
        except Exception as e:
            logger.error(f"Tool call failed for {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name,
                "execution_time_ms": 0
            }
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available tools for LLM function calling"""
        return self.available_tools.copy()
    
    def format_tools_for_ollama(self) -> List[Dict[str, Any]]:
        """
        Format available tools for Ollama function calling.
        
        Returns:
            List of tool definitions in Ollama function calling format
        """
        ollama_tools = []
        
        for tool_name, tool_info in self.available_tools.items():
            ollama_tool = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info["description"],
                    "parameters": tool_info.get("input_schema", {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                }
            }
            ollama_tools.append(ollama_tool)
        
        return ollama_tools
    
    async def process_tool_calls(self, 
                                tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple tool calls from Ollama.
        
        Args:
            tool_calls: List of tool calls from Ollama
            
        Returns:
            List of tool call results
        """
        results = []
        
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            tool_name = function.get("name")
            arguments = function.get("arguments", {})
            
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            
            result = await self.call_tool(tool_name, arguments)
            
            # Format result for Ollama
            results.append({
                "tool_call_id": tool_call.get("id", str(uuid.uuid4())),
                "role": "tool",
                "name": tool_name,
                "content": result.get("result", result.get("error", "Tool execution failed"))
            })
        
        return results
    
    async def close(self) -> None:
        """Close MCP client and cleanup resources"""
        if self.process:
            try:
                # Send shutdown if process is still alive
                if self.process.poll() is None:
                    self.process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait()
                        
            except Exception as e:
                logger.error(f"Error closing MCP client: {e}")
            finally:
                self.process = None
        
        self.is_initialized = False
        logger.info("MCP client closed")


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None


async def get_mcp_client() -> MCPClient:
    """Get or create global MCP client instance"""
    global _mcp_client
    
    if not settings.mcp_enabled:
        raise MCPClientError("MCP is disabled in settings")
    
    if _mcp_client is None:
        _mcp_client = MCPClient()
        await _mcp_client.initialize()
    
    return _mcp_client


async def close_mcp_client() -> None:
    """Close global MCP client"""
    global _mcp_client
    if _mcp_client:
        await _mcp_client.close()
        _mcp_client = None