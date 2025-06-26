"""
MCP Client for the gateway service.

This client is provider-agnostic and works with any LLM provider through
the existing model registry system. It handles tool discovery, execution,
and result formatting in a standardized way.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import uuid

from ..exceptions import BaseServiceError
from .base import MCPServerConfig, TransportType, ToolCall, ToolResult, ToolApprovalStatus
from .tool_registry import ToolRegistry
from .tool_approval import ToolApprovalService
from .protocol import JSONRPCProtocol, MCPMethods, JSONRPCError
from .transports import HTTPTransport

logger = logging.getLogger(__name__)


class MCPClientError(BaseServiceError):
    """MCP client specific errors."""
    pass


class MCPClient:
    """
    Provider-agnostic MCP client for the gateway service.
    
    This client:
    - Connects to MCP servers to discover and execute tools
    - Works with ANY LLM provider through the model registry
    - Manages tool approvals and execution
    - Formats tools for LLM consumption in a standardized way
    """
    
    def __init__(self, 
                 server_config: MCPServerConfig,
                 tool_registry: ToolRegistry,
                 approval_service: ToolApprovalService):
        """
        Initialize MCP client.
        
        Args:
            server_config: Configuration for connecting to MCP server
            tool_registry: Registry for managing discovered tools
            approval_service: Service for handling tool approvals
        """
        self.server_config = server_config
        self.tool_registry = tool_registry
        self.approval_service = approval_service
        self.transport = None
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize connection to MCP server and discover tools."""
        if self._initialized:
            return
            
        try:
            # Create transport based on config
            if self.server_config.transport_type == TransportType.HTTP:
                self.transport = HTTPTransport(self.server_config)
            else:
                raise MCPClientError(f"Unsupported transport type: {self.server_config.transport_type}")
            
            # Connect to server
            await self.transport.connect()
            
            # Initialize MCP protocol
            await self._initialize_protocol()
            
            # Discover available tools
            await self._discover_tools()
            
            self._initialized = True
            logger.info(f"MCP client initialized with {len(self.tool_registry.get_all_tools())} tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            await self.close()
            raise MCPClientError(f"MCP initialization failed: {e}")
    
    async def _initialize_protocol(self) -> None:
        """Send initialize message to MCP server."""
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "clientInfo": {
                "name": "privategpt-gateway",
                "version": "1.0.0"
            }
        }
        
        result = await self.transport.send_request(MCPMethods.INITIALIZE, params)
        logger.debug(f"MCP server initialized: {result}")
    
    async def _discover_tools(self) -> None:
        """Discover and register available tools from MCP server."""
        if not self.tool_registry.should_refresh():
            return
            
        result = await self.transport.send_request(MCPMethods.TOOLS_LIST)
        tools = result.get("tools", [])
        
        # Clear existing tools if doing full refresh
        self.tool_registry.clear()
        
        # Register each discovered tool
        for tool_data in tools:
            tool = self._parse_tool_definition(tool_data)
            if tool:
                self.tool_registry.register_tool(tool)
        
        self.tool_registry.mark_discovery_complete()
        logger.info(f"Discovered {len(tools)} tools from MCP server")
    
    def _parse_tool_definition(self, tool_data: Dict[str, Any]) -> Optional['Tool']:
        """Parse MCP tool definition into our Tool format."""
        from .base import Tool, ToolParameter
        
        try:
            name = tool_data.get("name")
            if not name:
                return None
                
            description = tool_data.get("description", "")
            input_schema = tool_data.get("inputSchema", {})
            
            # Parse parameters from JSON schema
            parameters = []
            if "properties" in input_schema:
                required_params = set(input_schema.get("required", []))
                
                for param_name, param_schema in input_schema["properties"].items():
                    param = ToolParameter(
                        name=param_name,
                        type=param_schema.get("type", "string"),
                        description=param_schema.get("description"),
                        required=param_name in required_params,
                        default=param_schema.get("default"),
                        enum=param_schema.get("enum")
                    )
                    parameters.append(param)
            
            # Determine category based on tool name or description
            category = self._infer_tool_category(name, description)
            
            return Tool(
                name=name,
                description=description,
                parameters=parameters,
                category=category
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse tool definition: {e}")
            return None
    
    def _infer_tool_category(self, name: str, description: str) -> str:
        """Infer tool category from name and description."""
        name_lower = name.lower()
        desc_lower = description.lower()
        
        if any(word in name_lower for word in ["calc", "math", "compute"]):
            return "calculation"
        elif any(word in name_lower for word in ["search", "find", "query"]):
            return "search"
        elif any(word in name_lower for word in ["file", "read", "write", "create"]):
            return "file_system"
        elif any(word in name_lower for word in ["time", "date", "clock"]):
            return "utility"
        elif any(word in desc_lower for word in ["system", "info", "status"]):
            return "system"
        else:
            return "general"
    
    async def execute_tool(self,
                          tool_call: ToolCall,
                          require_approval: bool = True) -> ToolResult:
        """
        Execute a tool call with approval handling.
        
        Args:
            tool_call: The tool call to execute
            require_approval: Whether to check approval requirements
            
        Returns:
            ToolResult with execution outcome
        """
        if not self._initialized:
            await self.initialize()
        
        # Validate tool call
        is_valid, error_msg = self.tool_registry.validate_tool_call(
            tool_call.tool_name,
            tool_call.arguments
        )
        if not is_valid:
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                error=error_msg
            )
        
        # Handle approval if required
        if require_approval and tool_call.requires_approval(self.tool_registry):
            approval = await self.approval_service.request_approval(tool_call)
            
            # If not auto-approved, wait for user decision
            if approval.tool_call.approval_status == ToolApprovalStatus.PENDING:
                status = await self.approval_service.wait_for_approval(approval.id)
                
                if status != ToolApprovalStatus.APPROVED and status != ToolApprovalStatus.AUTO_APPROVED:
                    return ToolResult(
                        tool_call_id=tool_call.id,
                        success=False,
                        error=f"Tool call was {status.value}"
                    )
        
        # Execute the tool
        try:
            start_time = datetime.now()
            
            params = {
                "name": tool_call.tool_name,
                "arguments": tool_call.arguments
            }
            
            result = await self.transport.send_request(MCPMethods.TOOLS_CALL, params)
            
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Extract content from MCP response
            content = self._extract_content(result)
            
            return ToolResult(
                tool_call_id=tool_call.id,
                success=True,
                result=content,
                execution_time_ms=execution_time_ms,
                metadata={"raw_response": result}
            )
            
        except JSONRPCError as e:
            logger.error(f"Tool execution RPC error: {e}")
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                error=f"Tool error: {e.message}"
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                error=str(e)
            )
    
    def _extract_content(self, mcp_result: Dict[str, Any]) -> Any:
        """Extract content from MCP tool result."""
        # MCP returns content as an array of content items
        if "content" in mcp_result:
            content_items = mcp_result["content"]
            if isinstance(content_items, list):
                # Combine text content items
                text_parts = []
                for item in content_items:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                return "\n".join(text_parts) if text_parts else mcp_result
            return content_items
        return mcp_result
    
    def get_tools_for_llm(self, 
                         user_role: str,
                         model_provider: str) -> List[Dict[str, Any]]:
        """
        Get tool definitions formatted for any LLM provider.
        
        This method returns tools in a standardized format that can be
        adapted by each provider's adapter.
        
        Args:
            user_role: Role of the user (for access control)
            model_provider: Name of the LLM provider (for format hints)
            
        Returns:
            List of tool definitions in standardized format
        """
        # Get tools available for this user
        tools = self.tool_registry.get_tools_for_llm(user_role)
        
        # Return in standardized format
        # Each provider adapter will transform this as needed
        formatted_tools = []
        for tool in tools:
            formatted_tool = {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
                "requires_approval": tool.get("requires_approval", False),
                "auto_approved": tool.get("auto_approved_for_user", False)
            }
            
            # Add provider-specific hints if needed
            if model_provider == "openai":
                formatted_tool["type"] = "function"
            elif model_provider == "anthropic":
                formatted_tool["input_schema"] = tool["parameters"]
                
            formatted_tools.append(formatted_tool)
            
        return formatted_tools
    
    async def close(self) -> None:
        """Close MCP client and cleanup resources."""
        if self.transport:
            try:
                await self.transport.disconnect()
            except Exception as e:
                logger.error(f"Error closing MCP transport: {e}")
            finally:
                self.transport = None
        
        self._initialized = False
        logger.info("MCP client closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()