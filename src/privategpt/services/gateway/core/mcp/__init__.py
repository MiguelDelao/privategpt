"""
MCP (Model Context Protocol) integration for the gateway service.

This package provides the MCP client implementation that enables the gateway
to discover and execute tools from MCP servers.
"""

from .base import (
    Tool,
    ToolCall,
    ToolResult,
    ToolApprovalStatus,
    TransportType,
    MCPServerConfig,
)
from .tool_registry import ToolRegistry
from .tool_approval import ToolApprovalService, ApprovalRequest
from .protocol import JSONRPCProtocol, MCPMethods
from .mcp_client import MCPClient, MCPClientError

__all__ = [
    "Tool",
    "ToolCall", 
    "ToolResult",
    "ToolApprovalStatus",
    "TransportType",
    "MCPServerConfig",
    "ToolRegistry",
    "ToolApprovalService",
    "ApprovalRequest",
    "JSONRPCProtocol",
    "MCPMethods",
    "MCPClient",
    "MCPClientError",
]