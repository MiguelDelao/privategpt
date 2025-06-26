"""
MCP Tool Approval Service with WebSocket notifications.

This service handles the approval workflow for MCP tool execution:
- Creates approval requests in database
- Sends real-time notifications via WebSocket
- Manages approval timeouts and expiration
- Provides approval status checking
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from privategpt.infra.database.models import MCPApproval, ApprovalStatus, User
from privategpt.infra.database.async_session import get_async_db_session
from privategpt.infra.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)


@dataclass
class ApprovalRequest:
    """Approval request for UI display."""
    id: str
    tool_name: str
    tool_description: str
    arguments: Dict[str, any]
    conversation_id: str
    user_id: str
    requested_at: datetime
    expires_at: datetime
    time_remaining_seconds: int
    
    @classmethod
    def from_db_model(cls, db_approval: MCPApproval) -> 'ApprovalRequest':
        """Create ApprovalRequest from database model."""
        now = datetime.utcnow()
        time_remaining = max(0, int((db_approval.expires_at - now).total_seconds()))
        
        return cls(
            id=db_approval.id,
            tool_name=db_approval.tool_name,
            tool_description=db_approval.tool_description or f"Execute {db_approval.tool_name}",
            arguments=db_approval.tool_arguments or {},
            conversation_id=db_approval.conversation_id or "",
            user_id=str(db_approval.user_id),
            requested_at=db_approval.requested_at,
            expires_at=db_approval.expires_at,
            time_remaining_seconds=time_remaining
        )


@dataclass
class ApprovalResponse:
    """Response after approval decision."""
    id: str
    approved: bool
    reviewed_by: str
    reviewed_at: datetime
    reason: Optional[str] = None


class WebSocketManager:
    """Manages WebSocket connections for real-time notifications."""
    
    def __init__(self):
        self.connections: Dict[str, Set[any]] = {}  # user_id -> set of websocket connections
        self.conversation_connections: Dict[str, Set[any]] = {}  # conversation_id -> connections
    
    def add_connection(self, websocket, user_id: str, conversation_id: Optional[str] = None):
        """Add a WebSocket connection for notifications."""
        if user_id not in self.connections:
            self.connections[user_id] = set()
        self.connections[user_id].add(websocket)
        
        if conversation_id:
            if conversation_id not in self.conversation_connections:
                self.conversation_connections[conversation_id] = set()
            self.conversation_connections[conversation_id].add(websocket)
        
        logger.debug(f"Added WebSocket connection for user {user_id}")
    
    def remove_connection(self, websocket, user_id: str, conversation_id: Optional[str] = None):
        """Remove a WebSocket connection."""
        if user_id in self.connections:
            self.connections[user_id].discard(websocket)
            if not self.connections[user_id]:
                del self.connections[user_id]
        
        if conversation_id and conversation_id in self.conversation_connections:
            self.conversation_connections[conversation_id].discard(websocket)
            if not self.conversation_connections[conversation_id]:
                del self.conversation_connections[conversation_id]
        
        logger.debug(f"Removed WebSocket connection for user {user_id}")
    
    async def notify_user(self, user_id: str, message: Dict[str, any]):
        """Send notification to all connections for a user."""
        if user_id not in self.connections:
            return
        
        disconnected = set()
        message_json = json.dumps(message)
        
        for websocket in self.connections[user_id]:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message to user {user_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            self.connections[user_id].discard(ws)
    
    async def notify_conversation(self, conversation_id: str, message: Dict[str, any]):
        """Send notification to all connections for a conversation."""
        if conversation_id not in self.conversation_connections:
            return
        
        disconnected = set()
        message_json = json.dumps(message)
        
        for websocket in self.conversation_connections[conversation_id]:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message to conversation {conversation_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            self.conversation_connections[conversation_id].discard(ws)
    
    async def broadcast_admin(self, message: Dict[str, any]):
        """Broadcast message to all admin users."""
        # This would query for admin users and send to all their connections
        # For simplicity, we'll send to all connections for now
        message_json = json.dumps(message)
        
        for user_connections in self.connections.values():
            for websocket in user_connections.copy():
                try:
                    await websocket.send_text(message_json)
                except Exception:
                    pass  # Ignore errors for broadcast


class ToolApprovalService:
    """Enhanced tool approval service with real-time notifications."""
    
    def __init__(self, default_timeout: int = 300):
        self.default_timeout = default_timeout
        self.redis = get_redis_client()
        self.websocket_manager = WebSocketManager()
        self._cleanup_task = None
        
        # Start cleanup task
        asyncio.create_task(self._start_cleanup_task())
    
    async def _start_cleanup_task(self):
        """Start background task to clean up expired approvals."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_approvals())
    
    async def _cleanup_expired_approvals(self):
        """Background task to mark expired approvals."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                async with get_async_db_session() as db:
                    # Find expired pending approvals
                    expired_query = select(MCPApproval).where(
                        and_(
                            MCPApproval.status == ApprovalStatus.PENDING,
                            MCPApproval.expires_at <= datetime.utcnow()
                        )
                    )
                    
                    result = await db.execute(expired_query)
                    expired_approvals = result.scalars().all()
                    
                    for approval in expired_approvals:
                        approval.status = ApprovalStatus.EXPIRED
                        
                        # Notify about expiration
                        await self._notify_approval_expired(approval)
                    
                    if expired_approvals:
                        await db.commit()
                        logger.info(f"Marked {len(expired_approvals)} approvals as expired")
                        
            except Exception as e:
                logger.error(f"Error in approval cleanup task: {e}")
    
    async def request_approval(
        self,
        tool_name: str,
        tool_description: str,
        arguments: Dict[str, any],
        user_id: str,
        conversation_id: str,
        timeout_seconds: Optional[int] = None
    ) -> ApprovalRequest:
        """Request approval for a tool execution."""
        approval_id = f"approval_{uuid.uuid4().hex[:8]}"
        timeout = timeout_seconds or self.default_timeout
        
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=timeout)
        
        # Create database record
        async with get_async_db_session() as db:
            approval = MCPApproval(
                id=approval_id,
                tool_name=tool_name,
                tool_description=tool_description,
                tool_arguments=arguments,
                user_id=int(user_id),
                conversation_id=conversation_id,
                status=ApprovalStatus.PENDING,
                requested_at=now,
                expires_at=expires_at
            )
            
            db.add(approval)
            await db.commit()
            await db.refresh(approval)
        
        # Create approval request object
        request = ApprovalRequest.from_db_model(approval)
        
        # Cache in Redis for quick access
        await self._cache_approval_request(request)
        
        # Send real-time notification
        await self._notify_approval_requested(request)
        
        logger.info(f"Approval requested: {approval_id} for tool {tool_name} by user {user_id}")
        return request
    
    async def _cache_approval_request(self, request: ApprovalRequest):
        """Cache approval request in Redis."""
        try:
            await self.redis.connect()
            cache_key = f"approval:{request.id}"
            
            await self.redis.redis.setex(
                cache_key,
                self.default_timeout + 60,  # Extra 60 seconds for cleanup
                json.dumps(asdict(request), default=str)
            )
        except Exception as e:
            logger.warning(f"Failed to cache approval request {request.id}: {e}")
    
    async def _notify_approval_requested(self, request: ApprovalRequest):
        """Send notification about new approval request."""
        notification = {
            "type": "approval_requested",
            "data": {
                "approval_id": request.id,
                "tool_name": request.tool_name,
                "tool_description": request.tool_description,
                "arguments": request.arguments,
                "conversation_id": request.conversation_id,
                "expires_at": request.expires_at.isoformat(),
                "time_remaining_seconds": request.time_remaining_seconds
            }
        }
        
        # Notify the user who made the request
        await self.websocket_manager.notify_user(request.user_id, notification)
        
        # Notify others in the conversation
        if request.conversation_id:
            await self.websocket_manager.notify_conversation(request.conversation_id, notification)
        
        # Notify admin users
        admin_notification = {
            **notification,
            "data": {
                **notification["data"],
                "user_id": request.user_id
            }
        }
        await self.websocket_manager.broadcast_admin(admin_notification)
    
    async def _notify_approval_expired(self, approval: MCPApproval):
        """Send notification about expired approval."""
        notification = {
            "type": "approval_expired",
            "data": {
                "approval_id": approval.id,
                "tool_name": approval.tool_name,
                "conversation_id": approval.conversation_id
            }
        }
        
        # Notify the user
        await self.websocket_manager.notify_user(str(approval.user_id), notification)
        
        # Notify conversation
        if approval.conversation_id:
            await self.websocket_manager.notify_conversation(approval.conversation_id, notification)
    
    async def approve_tool(
        self,
        approval_id: str,
        user_id: str,
        approved: bool,
        reason: Optional[str] = None
    ) -> ApprovalResponse:
        """Approve or reject a tool execution."""
        async with get_async_db_session() as db:
            # Get approval record
            approval = await db.get(MCPApproval, approval_id)
            if not approval:
                raise ValueError(f"Approval {approval_id} not found")
            
            if approval.status != ApprovalStatus.PENDING:
                raise ValueError(f"Approval {approval_id} is not pending (status: {approval.status})")
            
            # Check if expired
            if datetime.utcnow() > approval.expires_at:
                approval.status = ApprovalStatus.EXPIRED
                await db.commit()
                raise ValueError(f"Approval {approval_id} has expired")
            
            # Update approval
            approval.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
            approval.reviewed_by = int(user_id)
            approval.reviewed_at = datetime.utcnow()
            approval.review_reason = reason
            
            await db.commit()
            await db.refresh(approval)
        
        response = ApprovalResponse(
            id=approval_id,
            approved=approved,
            reviewed_by=user_id,
            reviewed_at=approval.reviewed_at,
            reason=reason
        )
        
        # Remove from cache
        await self._remove_approval_from_cache(approval_id)
        
        # Send notification
        await self._notify_approval_decided(approval, response)
        
        logger.info(f"Approval {approval_id} {'approved' if approved else 'rejected'} by user {user_id}")
        return response
    
    async def _remove_approval_from_cache(self, approval_id: str):
        """Remove approval from Redis cache."""
        try:
            await self.redis.connect()
            await self.redis.redis.delete(f"approval:{approval_id}")
        except Exception as e:
            logger.warning(f"Failed to remove approval from cache {approval_id}: {e}")
    
    async def _notify_approval_decided(self, approval: MCPApproval, response: ApprovalResponse):
        """Send notification about approval decision."""
        notification = {
            "type": "approval_decided",
            "data": {
                "approval_id": approval.id,
                "tool_name": approval.tool_name,
                "approved": response.approved,
                "reviewed_by": response.reviewed_by,
                "reviewed_at": response.reviewed_at.isoformat(),
                "reason": response.reason,
                "conversation_id": approval.conversation_id
            }
        }
        
        # Notify the original user
        await self.websocket_manager.notify_user(str(approval.user_id), notification)
        
        # Notify conversation
        if approval.conversation_id:
            await self.websocket_manager.notify_conversation(approval.conversation_id, notification)
    
    async def get_pending_approvals(
        self,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> List[ApprovalRequest]:
        """Get pending approval requests."""
        async with get_async_db_session() as db:
            query = select(MCPApproval).where(
                and_(
                    MCPApproval.status == ApprovalStatus.PENDING,
                    MCPApproval.expires_at > datetime.utcnow()
                )
            )
            
            if user_id:
                query = query.where(MCPApproval.user_id == int(user_id))
            
            if conversation_id:
                query = query.where(MCPApproval.conversation_id == conversation_id)
            
            result = await db.execute(query)
            approvals = result.scalars().all()
            
            return [ApprovalRequest.from_db_model(approval) for approval in approvals]
    
    async def get_approval_status(self, approval_id: str) -> Optional[ApprovalStatus]:
        """Get current status of an approval."""
        async with get_async_db_session() as db:
            approval = await db.get(MCPApproval, approval_id)
            return approval.status if approval else None
    
    async def get_approval_history(
        self,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, any]]:
        """Get approval history."""
        async with get_async_db_session() as db:
            query = select(MCPApproval).order_by(MCPApproval.requested_at.desc()).limit(limit)
            
            if user_id:
                query = query.where(MCPApproval.user_id == int(user_id))
            
            if conversation_id:
                query = query.where(MCPApproval.conversation_id == conversation_id)
            
            result = await db.execute(query)
            approvals = result.scalars().all()
            
            history = []
            for approval in approvals:
                history.append({
                    "id": approval.id,
                    "tool_name": approval.tool_name,
                    "tool_description": approval.tool_description,
                    "arguments": approval.tool_arguments,
                    "status": approval.status.value,
                    "requested_at": approval.requested_at.isoformat(),
                    "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
                    "reviewed_by": approval.reviewed_by,
                    "execution_duration_ms": approval.execution_duration_ms,
                    "execution_error": approval.execution_error
                })
            
            return history
    
    def add_websocket_connection(self, websocket, user_id: str, conversation_id: Optional[str] = None):
        """Add WebSocket connection for notifications."""
        self.websocket_manager.add_connection(websocket, user_id, conversation_id)
    
    def remove_websocket_connection(self, websocket, user_id: str, conversation_id: Optional[str] = None):
        """Remove WebSocket connection."""
        self.websocket_manager.remove_connection(websocket, user_id, conversation_id)
    
    async def cleanup(self):
        """Clean up resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        await self.redis.close()


# Global approval service instance
_approval_service: Optional[ToolApprovalService] = None


def get_approval_service() -> ToolApprovalService:
    """Get global approval service instance."""
    global _approval_service
    if _approval_service is None:
        _approval_service = ToolApprovalService()
    return _approval_service