"""
Unified MCP Client with HTTP-only transport and simplified approval workflow.

This is the production-ready MCP client that replaces the complex multi-transport
implementation with a simple, robust HTTP-only approach.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.infra.database.models import MCPApproval, ApprovalStatus
from privategpt.infra.database.async_session import get_async_db_session

logger = logging.getLogger(__name__)


@dataclass
class TransportConfig:
    """HTTP transport configuration."""
    timeout: int = 30
    max_attempts: int = 3
    backoff: float = 1.5


@dataclass
class MCPServerConfig:
    """MCP Server configuration."""
    name: str
    base_url: str
    auth_token: Optional[str] = None
    health_check_enabled: bool = True
    health_check_interval: int = 30


@dataclass
class MCPConfig:
    """Main MCP configuration."""
    transport: TransportConfig
    servers: List[MCPServerConfig]
    approval_timeout: int = 300  # 5 minutes


@dataclass
class Tool:
    """Tool definition from MCP server."""
    name: str
    description: str
    parameters: Dict[str, Any]
    server_name: str
    category: Optional[str] = None


@dataclass
class ToolCall:
    """Tool call request."""
    id: str
    tool_name: str
    arguments: Dict[str, Any]
    user_id: str
    conversation_id: str
    requires_approval: bool = True


@dataclass
class ToolResult:
    """Tool execution result."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


@dataclass
class ApprovalRequest:
    """Tool approval request for UI."""
    id: str
    tool_name: str
    tool_description: str
    arguments: Dict[str, Any]
    conversation_id: str
    requested_at: datetime
    expires_at: datetime


@dataclass
class UserContext:
    """User context for tool execution."""
    user_id: str
    conversation_id: str
    role: str
    auto_approve_tools: bool = False


class HTTPTransport:
    """Unified HTTP transport for MCP communication."""
    
    def __init__(self, config: TransportConfig):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
    
    async def connect(self):
        """Initialize HTTP client with connection pooling."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=self.config.timeout,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=10)
            )
    
    async def execute(self, server_url: str, method: str, params: Dict[str, Any], auth_token: Optional[str] = None) -> Any:
        """Execute JSON-RPC call to MCP server."""
        if self.client is None:
            await self.connect()
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": str(uuid.uuid4())
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        # Retry logic for resilience
        for attempt in range(self.config.max_attempts):
            try:
                response = await self.client.post(
                    f"{server_url}/rpc",
                    json=request,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                if "error" in result:
                    error_msg = result["error"].get("message", "Unknown error")
                    raise Exception(f"MCP Error: {error_msg}")
                    
                return result.get("result")
                    
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                if attempt == self.config.max_attempts - 1:
                    raise Exception(f"Transport failed after {self.config.max_attempts} attempts: {e}")
                await asyncio.sleep(self.config.backoff * (attempt + 1))
    
    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None


class ToolRegistry:
    """Tool discovery and management."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.server_tools: Dict[str, List[str]] = {}
    
    def register_tools(self, server_name: str, tools: List[Dict[str, Any]]):
        """Register tools from an MCP server."""
        tool_names = []
        
        for tool_data in tools:
            # Add server prefix to avoid conflicts
            full_name = f"{server_name}.{tool_data['name']}"
            
            params = tool_data.get("parameters", tool_data.get("inputSchema", {}))
            print(f"PRINT: Registering tool {full_name}")
            print(f"PRINT: Tool data: {tool_data}")
            print(f"PRINT: Parameters extracted: {params}")
            logger.info(f"[DEBUG] Registering tool {full_name}")
            logger.info(f"[DEBUG] Tool data: {tool_data}")
            logger.info(f"[DEBUG] Parameters extracted: {params}")
            
            tool = Tool(
                name=full_name,
                description=tool_data["description"],
                parameters=params,
                server_name=server_name,
                category=tool_data.get("category")
            )
            
            logger.info(f"[DEBUG] Tool object created: name={tool.name}, params={tool.parameters}")
            print(f"PRINT: Tool object created: {tool}")
            print(f"PRINT: Tool parameters type: {type(tool.parameters)}")
            
            self.tools[full_name] = tool
            tool_names.append(full_name)
        
        self.server_tools[server_name] = tool_names
        logger.info(f"Registered {len(tool_names)} tools from server {server_name}")
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get tool definition by name."""
        return self.tools.get(tool_name)
    
    def get_tools_for_llm(self, provider: str) -> List[Dict[str, Any]]:
        """Get tools formatted for specific LLM provider."""
        tools = []
        
        logger.info(f"[DEBUG] Formatting {len(self.tools)} tools for provider: {provider}")
        
        for tool_name, tool in self.tools.items():
            logger.info(f"[DEBUG] Tool {tool_name}: {tool}")
            if provider == "openai":
                tools.append(self._format_openai_tool(tool))
            elif provider == "anthropic":
                tools.append(self._format_anthropic_tool(tool))
            elif provider == "ollama":
                tools.append(self._format_ollama_tool(tool))
            else:
                tools.append(self._format_generic_tool(tool))
        
        return tools
    
    def _format_openai_tool(self, tool: Tool) -> Dict[str, Any]:
        """Format tool for OpenAI function calling."""
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
        }
    
    def _format_anthropic_tool(self, tool: Tool) -> Dict[str, Any]:
        """Format tool for Anthropic tools."""
        logger.info(f"[DEBUG] Formatting tool {tool.name} for Anthropic")
        logger.info(f"[DEBUG] Tool object: {tool}")
        logger.info(f"[DEBUG] Tool parameters: {tool.parameters}")
        logger.info(f"[DEBUG] Tool parameters type: {type(tool.parameters)}")
        
        # Anthropic requires tool names to match pattern '^[a-zA-Z0-9_-]{1,128}$'
        # Replace dots with underscores
        sanitized_name = tool.name.replace(".", "_")
        
        formatted = {
            "name": sanitized_name,
            "description": tool.description,
            "input_schema": tool.parameters
        }
        
        logger.info(f"[DEBUG] Formatted tool for Anthropic: {formatted}")
        
        return formatted
    
    def _format_ollama_tool(self, tool: Tool) -> Dict[str, Any]:
        """Format tool for Ollama function calling."""
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
        }
    
    def _format_generic_tool(self, tool: Tool) -> Dict[str, Any]:
        """Generic tool format."""
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters
        }


class ToolApprovalService:
    """Simple approval service for tool execution."""
    
    def __init__(self):
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
    
    async def request_approval(self, tool_call: ToolCall, timeout_seconds: int = 300) -> str:
        """Request approval for a tool call. Returns approval ID."""
        approval_id = f"approval_{uuid.uuid4().hex[:8]}"
        
        # Get tool for description
        tool_name = tool_call.tool_name.split(".", 1)[-1]  # Remove server prefix
        
        request = ApprovalRequest(
            id=approval_id,
            tool_name=tool_call.tool_name,
            tool_description=f"Execute {tool_name}",
            arguments=tool_call.arguments,
            conversation_id=tool_call.conversation_id,
            requested_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=timeout_seconds)
        )
        
        # Store approval request in database
        async with get_async_db_session() as db:
            approval = MCPApproval(
                id=approval_id,
                tool_name=tool_call.tool_name,
                tool_description=request.tool_description,
                tool_arguments=tool_call.arguments,
                user_id=int(tool_call.user_id),
                conversation_id=tool_call.conversation_id,
                status=ApprovalStatus.PENDING,
                requested_at=request.requested_at,
                expires_at=request.expires_at
            )
            db.add(approval)
            await db.commit()
        
        self.pending_approvals[approval_id] = request
        logger.info(f"Approval requested for {tool_call.tool_name}: {approval_id}")
        
        return approval_id
    
    async def check_approval(self, approval_id: str) -> Optional[bool]:
        """Check if approval has been granted/denied. Returns None if still pending."""
        async with get_async_db_session() as db:
            approval = await db.get(MCPApproval, approval_id)
            if not approval:
                return None
            
            if approval.status == ApprovalStatus.APPROVED:
                return True
            elif approval.status in [ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED]:
                return False
            
            # Check for timeout
            if datetime.utcnow() > approval.expires_at:
                approval.status = ApprovalStatus.EXPIRED
                await db.commit()
                return False
        
        return None  # Still pending
    
    async def approve_tool(self, approval_id: str, user_id: str, approved: bool, reason: Optional[str] = None):
        """Approve or reject a tool execution."""
        async with get_async_db_session() as db:
            approval = await db.get(MCPApproval, approval_id)
            if not approval:
                raise ValueError(f"Approval {approval_id} not found")
            
            approval.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
            approval.reviewed_by = int(user_id)
            approval.reviewed_at = datetime.utcnow()
            approval.review_reason = reason
            
            await db.commit()
            
            # Remove from pending
            self.pending_approvals.pop(approval_id, None)
            
            logger.info(f"Approval {approval_id} {'approved' if approved else 'rejected'} by {user_id}")


class MCPClient:
    """Unified MCP client with HTTP transport and simple approval workflow."""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.transport = HTTPTransport(config.transport)
        self.registry = ToolRegistry()
        self.approval_service = ToolApprovalService()
        self.servers: Dict[str, MCPServerConfig] = {}
    
    async def initialize(self):
        """Initialize MCP client and discover tools from all servers."""
        await self.transport.connect()
        
        for server_config in self.config.servers:
            await self._connect_server(server_config)
    
    async def _connect_server(self, server_config: MCPServerConfig):
        """Connect to an MCP server and discover its tools."""
        try:
            # Discover tools from server
            tools = await self.transport.execute(
                server_config.base_url,
                "tools/list",
                {},
                server_config.auth_token
            )
            
            # Register tools
            if tools and "tools" in tools:
                self.registry.register_tools(server_config.name, tools["tools"])
                self.servers[server_config.name] = server_config
                logger.info(f"Connected to MCP server: {server_config.name}")
            else:
                logger.warning(f"No tools found on server: {server_config.name}")
                
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_config.name}: {e}")
    
    def get_tools_for_llm(self, provider: str) -> List[Dict[str, Any]]:
        """Get all available tools formatted for LLM provider."""
        return self.registry.get_tools_for_llm(provider)
    
    async def execute_tool(self, tool_call: ToolCall, user_context: UserContext) -> ToolResult:
        """Execute a tool with optional approval workflow."""
        start_time = datetime.utcnow()
        
        try:
            # Get tool definition
            tool = self.registry.get_tool(tool_call.tool_name)
            if not tool:
                return ToolResult(
                    success=False,
                    error=f"Tool {tool_call.tool_name} not found"
                )
            
            # Check if approval needed
            needs_approval = not user_context.auto_approve_tools
            
            if needs_approval:
                # Request approval
                approval_id = await self.approval_service.request_approval(
                    tool_call, 
                    self.config.approval_timeout
                )
                
                # Wait for approval (this would be handled by the streaming chat)
                # For now, return with approval pending
                return ToolResult(
                    success=False,
                    error=f"Approval required: {approval_id}"
                )
            
            # Execute the tool
            server_config = self.servers[tool.server_name]
            result = await self.transport.execute(
                server_config.base_url,
                "tools/call",
                {
                    "name": tool_call.tool_name.split(".", 1)[-1],  # Remove server prefix
                    "arguments": tool_call.arguments
                },
                server_config.auth_token
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ToolResult(
                success=True,
                result=result,
                execution_time_ms=int(execution_time)
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=int(execution_time)
            )
    
    async def execute_approved_tool(self, approval_id: str) -> ToolResult:
        """Execute a tool that has been approved."""
        async with get_async_db_session() as db:
            approval = await db.get(MCPApproval, approval_id)
            if not approval or approval.status != ApprovalStatus.APPROVED:
                return ToolResult(
                    success=False,
                    error="Tool not approved or approval not found"
                )
            
            # Create tool call from approval
            tool_call = ToolCall(
                id=approval_id,
                tool_name=approval.tool_name,
                arguments=approval.tool_arguments,
                user_id=str(approval.user_id),
                conversation_id=approval.conversation_id,
                requires_approval=False  # Already approved
            )
            
            # Execute with auto-approve context
            user_context = UserContext(
                user_id=str(approval.user_id),
                conversation_id=approval.conversation_id,
                role="user",
                auto_approve_tools=True  # Skip approval since it's already approved
            )
            
            result = await self.execute_tool(tool_call, user_context)
            
            # Update approval record with execution result
            approval.execution_result = result.result if result.success else None
            approval.execution_error = result.error
            approval.execution_duration_ms = result.execution_time_ms
            
            await db.commit()
            
            return result
    
    async def get_pending_approvals(self, user_id: Optional[str] = None) -> List[ApprovalRequest]:
        """Get pending approval requests."""
        from sqlalchemy import select
        async with get_async_db_session() as db:
            query = select(MCPApproval).filter(
                MCPApproval.status == ApprovalStatus.PENDING,
                MCPApproval.expires_at > datetime.utcnow()
            )
            
            if user_id:
                query = query.filter(MCPApproval.user_id == int(user_id))
            
            result = await db.execute(query)
            approvals = result.scalars().all()
            
            return [
                ApprovalRequest(
                    id=approval.id,
                    tool_name=approval.tool_name,
                    tool_description=approval.tool_description or "Tool execution",
                    arguments=approval.tool_arguments,
                    conversation_id=approval.conversation_id,
                    requested_at=approval.requested_at,
                    expires_at=approval.expires_at
                )
                for approval in approvals
            ]
    
    async def close(self):
        """Close the MCP client and clean up resources."""
        await self.transport.close()


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None


async def get_mcp_client() -> MCPClient:
    """Get the global MCP client instance."""
    global _mcp_client
    
    logger.info("[DEBUG] get_mcp_client called")
    
    # Force re-initialization for debugging
    _mcp_client = None
    
    if _mcp_client is None:
        logger.info("[DEBUG] Creating new MCP client instance")
        # Default configuration - this would come from config file
        config = MCPConfig(
            transport=TransportConfig(),
            servers=[
                MCPServerConfig(
                    name="rag",
                    base_url="http://privategpt-mcp-service-1:8000"
                )
            ]
        )
        
        _mcp_client = MCPClient(config)
        await _mcp_client.initialize()
        logger.info(f"[DEBUG] MCP client initialized with {len(_mcp_client.registry.tools)} tools")
    else:
        logger.info(f"[DEBUG] Returning existing MCP client with {len(_mcp_client.registry.tools)} tools")
    
    return _mcp_client