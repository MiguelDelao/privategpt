"""
Base classes and types for MCP (Model Context Protocol) integration.

This module defines the core types and interfaces used throughout the MCP client
implementation in the gateway service.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from datetime import datetime


class ToolApprovalStatus(Enum):
    """Status of a tool call approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    EXPIRED = "expired"


class TransportType(Enum):
    """Types of transport protocols supported by MCP."""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


@dataclass
class ToolParameter:
    """Represents a parameter for an MCP tool."""
    name: str
    type: str  # "string", "number", "boolean", "object", "array"
    description: Optional[str] = None
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    properties: Optional[Dict[str, 'ToolParameter']] = None  # For object types


@dataclass
class Tool:
    """Represents an MCP tool definition."""
    name: str
    description: str
    parameters: List[ToolParameter]
    requires_approval: bool = False
    auto_approve_for: Optional[List[str]] = None  # List of user roles that can auto-approve
    category: Optional[str] = None  # e.g., "search", "calculation", "file_system"
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert tool definition to JSON Schema format for LLM."""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param in self.parameters:
            schema["properties"][param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                schema["properties"][param.name]["enum"] = param.enum
            if param.required:
                schema["required"].append(param.name)
                
        return {
            "name": self.name,
            "description": self.description,
            "parameters": schema
        }


@dataclass
class ToolCall:
    """Represents a request to call an MCP tool."""
    id: str  # Unique identifier for this tool call
    tool_name: str
    arguments: Dict[str, Any]
    conversation_id: str
    user_id: str
    requested_at: datetime
    approval_status: ToolApprovalStatus = ToolApprovalStatus.PENDING
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    def requires_approval(self, tool_registry: 'ToolRegistry') -> bool:
        """Check if this tool call requires approval."""
        tool = tool_registry.get_tool(self.tool_name)
        if not tool:
            return True  # Unknown tools always require approval
        
        # Check if user's role allows auto-approval
        # This would be implemented based on your auth system
        return tool.requires_approval


@dataclass
class ToolResult:
    """Represents the result of an MCP tool execution."""
    tool_call_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MCPRequest:
    """Represents a JSON-RPC request to MCP server."""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


@dataclass
class MCPResponse:
    """Represents a JSON-RPC response from MCP server."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


@dataclass
class MCPServerConfig:
    """Configuration for connecting to an MCP server."""
    name: str
    transport_type: TransportType
    # For HTTP transport
    base_url: Optional[str] = None
    # For stdio transport
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None
    # For websocket transport
    ws_url: Optional[str] = None
    # Common settings
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 1