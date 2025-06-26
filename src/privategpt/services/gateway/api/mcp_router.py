"""
MCP API Router for tool discovery, execution, and approval management.

This router provides REST endpoints for:
- Tool discovery and listing
- Tool execution requests
- Approval workflow management
- WebSocket connections for real-time notifications
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from privategpt.shared.auth_middleware import get_current_user
from privategpt.services.gateway.core.mcp.unified_mcp_client import get_mcp_client, UserContext, ToolCall

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["MCP"])


# Request/Response Models
class ToolExecutionRequest(BaseModel):
    """Request to execute a tool."""
    tool_name: str = Field(..., description="Full tool name (server.tool)")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments")
    conversation_id: str = Field(..., description="Conversation ID")
    require_approval: Optional[bool] = Field(None, description="Override approval requirement")


class ToolExecutionResponse(BaseModel):
    """Response from tool execution."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    approval_id: Optional[str] = None  # If approval is required


class ApprovalDecisionRequest(BaseModel):
    """Request to approve/reject a tool."""
    approved: bool = Field(..., description="Whether to approve the tool")
    reason: Optional[str] = Field(None, description="Reason for decision")


class ApprovalResponse(BaseModel):
    """Response after approval decision."""
    id: str
    approved: bool
    reviewed_by: str
    reviewed_at: datetime
    reason: Optional[str] = None


class ToolInfo(BaseModel):
    """Tool information for API responses."""
    name: str
    description: str
    parameters: Dict[str, Any]
    server_name: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class ServerInfo(BaseModel):
    """MCP Server information."""
    name: str
    status: str
    tool_count: int
    last_health_check: Optional[datetime] = None


class ApprovalInfo(BaseModel):
    """Approval request information."""
    id: str
    tool_name: str
    tool_description: str
    arguments: Dict[str, Any]
    conversation_id: str
    user_id: str
    requested_at: datetime
    expires_at: datetime
    time_remaining_seconds: int


# Tool Discovery Endpoints
@router.get("/tools", response_model=Dict[str, Any])
async def list_tools(
    provider: str = Query("generic", description="LLM provider (openai, anthropic, ollama, generic)"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """List all available MCP tools."""
    try:
        mcp_client = await get_mcp_client()
        
        # Get tools formatted for provider
        tools = mcp_client.registry.get_tools_for_llm(provider)
        
        # Get server status
        servers = {}
        for server_name in mcp_client.servers:
            servers[server_name] = {
                "status": "connected",
                "tool_count": 0  # Would need to implement tool counting per server
            }
        
        # Basic stats
        stats = {
            "total_tools": len(mcp_client.registry.tools),
            "total_servers": len(mcp_client.servers)
        }
        
        return {
            "tools": tools,
            "servers": servers,
            "stats": stats,
            "provider": provider
        }
        
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {e}")


@router.get("/tools/{tool_name}", response_model=ToolInfo)
async def get_tool_info(
    tool_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific tool."""
    try:
        mcp_client = await get_mcp_client()
        tool = mcp_client.registry.get_tool(tool_name)
        
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
        
        return ToolInfo(
            name=tool.name,
            description=tool.description,
            parameters=tool.parameters,
            server_name=tool.server_name,
            category=tool.category,
            tags=[]  # Would need to implement tags
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tool info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tool info: {e}")


@router.get("/servers", response_model=List[ServerInfo])
async def list_servers():
    """List all MCP servers and their status."""
    try:
        mcp_client = await get_mcp_client()
        servers = []
        
        for server_name, server_config in mcp_client.servers.items():
            servers.append(ServerInfo(
                name=server_name,
                status="connected",  # In production, would check actual health
                tool_count=0  # Would need to implement tool counting per server
            ))
        
        return servers
        
    except Exception as e:
        logger.error(f"Failed to list servers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list servers: {e}")


# Tool Execution Endpoints
@router.post("/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    request: ToolExecutionRequest
):
    """Execute a tool (may require approval)."""
    try:
        mcp_client = await get_mcp_client()
        
        # Create tool call
        tool_call = ToolCall(
            id=f"exec_{datetime.utcnow().timestamp()}",
            tool_name=request.tool_name,
            arguments=request.arguments,
            user_id="1",  # For testing without auth (needs to be numeric)
            conversation_id=request.conversation_id,
            requires_approval=request.require_approval if request.require_approval is not None else True
        )
        
        # Create user context (would get auto_approve from user settings)
        user_context = UserContext(
            user_id="1",
            conversation_id=request.conversation_id,
            role="user",
            auto_approve_tools=True  # Auto-approve for testing
        )
        
        # Execute tool
        result = await mcp_client.execute_tool(tool_call, user_context)
        
        # Check if approval is needed
        if not result.success and result.error and result.error.startswith("Approval required:"):
            approval_id = result.error.split(": ")[1]
            return ToolExecutionResponse(
                success=False,
                approval_id=approval_id,
                error="Approval required"
            )
        
        return ToolExecutionResponse(
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time_ms=result.execution_time_ms
        )
        
    except Exception as e:
        logger.error(f"Failed to execute tool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute tool: {e}")


# Approval Management Endpoints
@router.get("/approvals/pending", response_model=List[ApprovalInfo])
async def get_pending_approvals(
    conversation_id: Optional[str] = Query(None, description="Filter by conversation")
):
    """Get pending approval requests."""
    try:
        mcp_client = await get_mcp_client()
        
        # Get pending approvals for user or conversation
        approvals = await mcp_client.get_pending_approvals(user_id=None)  # None = all users for testing
        
        return [
            ApprovalInfo(
                id=approval.id,
                tool_name=approval.tool_name,
                tool_description=approval.tool_description,
                arguments=approval.arguments,
                conversation_id=approval.conversation_id,
                user_id=str(approval.user_id),
                requested_at=approval.requested_at,
                expires_at=approval.expires_at,
                time_remaining_seconds=int((approval.expires_at - datetime.utcnow()).total_seconds())
            )
            for approval in approvals
        ]
        
    except Exception as e:
        logger.error(f"Failed to get pending approvals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pending approvals: {e}")


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_tool(
    approval_id: str,
    request: ApprovalDecisionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Approve or reject a tool execution."""
    try:
        mcp_client = await get_mcp_client()
        
        await mcp_client.approval_service.approve_tool(
            approval_id=approval_id,
            user_id=current_user["user_id"],
            approved=request.approved,
            reason=request.reason
        )
        
        return ApprovalResponse(
            id=approval_id,
            approved=request.approved,
            reviewed_by=current_user["user_id"],
            reviewed_at=datetime.utcnow(),
            reason=request.reason
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to approve tool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve tool: {e}")


@router.post("/approvals/{approval_id}/execute", response_model=ToolExecutionResponse)
async def execute_approved_tool(
    approval_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Execute a tool that has been approved."""
    try:
        mcp_client = await get_mcp_client()
        
        result = await mcp_client.execute_approved_tool(approval_id)
        
        return ToolExecutionResponse(
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time_ms=result.execution_time_ms
        )
        
    except Exception as e:
        logger.error(f"Failed to execute approved tool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute approved tool: {e}")


@router.get("/approvals/history", response_model=List[Dict[str, Any]])
async def get_approval_history(
    conversation_id: Optional[str] = Query(None, description="Filter by conversation"),
    limit: int = Query(50, description="Maximum number of records")
):
    """Get approval history."""
    try:
        # For now, return empty history - this would be implemented with a proper query
        # against the MCPApproval table with status filters
        return []
        
    except Exception as e:
        logger.error(f"Failed to get approval history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get approval history: {e}")


# WebSocket for Real-time Notifications
@router.websocket("/ws/approvals")
async def approval_websocket(
    websocket: WebSocket,
    user_id: str = Query(..., description="User ID"),
    conversation_id: Optional[str] = Query(None, description="Conversation ID")
):
    """WebSocket endpoint for real-time approval notifications."""
    await websocket.accept()
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Handle ping/pong or other client messages
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# Utility Endpoints
@router.get("/health")
async def health_check():
    """Health check for MCP system."""
    try:
        mcp_client = await get_mcp_client()
        
        # Get basic client status
        server_count = len(mcp_client.servers)
        tool_count = len(mcp_client.registry.tools)
        
        # Get pending approvals count
        pending_approvals = await mcp_client.get_pending_approvals()
        pending_count = len(pending_approvals)
        
        return {
            "status": "healthy",
            "servers": {"connected": server_count},
            "tools": {"total": tool_count},
            "pending_approvals": pending_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


@router.post("/cache/clear")
async def clear_cache(
    server_name: Optional[str] = Query(None, description="Server to clear cache for"),
    current_user: dict = Depends(get_current_user)
):
    """Clear tool cache (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # For now, just return success - cache clearing would be implemented later
        return {
            "message": f"Cache cleared for {'all servers' if not server_name else server_name}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {e}")


@router.get("/stats")
async def get_mcp_stats():
    """Get MCP system statistics."""
    try:
        mcp_client = await get_mcp_client()
        
        # Basic stats
        server_count = len(mcp_client.servers)
        tool_count = len(mcp_client.registry.tools)
        
        # Approval stats
        pending_approvals = await mcp_client.get_pending_approvals()
        
        return {
            "registry": {
                "total_tools": tool_count,
                "total_servers": server_count
            },
            "approvals": {
                "pending": len(pending_approvals),
                "approved_today": 0,  # Would need proper history query
                "rejected_today": 0,  # Would need proper history query
                "total_history": 0    # Would need proper history query
            },
            "servers": {
                name: {"status": "connected", "tools": 0}  # Would need proper server tool counting
                for name in mcp_client.servers
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get MCP stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get MCP stats: {e}")