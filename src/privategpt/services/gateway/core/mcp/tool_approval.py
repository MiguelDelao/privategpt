"""
Tool Approval Service for managing tool call approvals.

This module handles the approval workflow for tool calls that require user consent
before execution. It supports both manual approval (through UI) and auto-approval
based on user roles and settings.
"""

import asyncio
import logging
import uuid
from typing import Dict, Optional, List, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .base import ToolCall, ToolApprovalStatus, Tool
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class ApprovalRequest:
    """Represents a pending approval request for a tool call."""
    id: str
    tool_call: ToolCall
    tool_info: Tool
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=5))
    approval_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if this approval request has expired."""
        return datetime.now() > self.expires_at
    
    def to_ui_format(self) -> Dict[str, Any]:
        """Format approval request for UI display."""
        return {
            "id": self.id,
            "tool_name": self.tool_call.tool_name,
            "tool_description": self.tool_info.description,
            "arguments": self.tool_call.arguments,
            "conversation_id": self.tool_call.conversation_id,
            "requested_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "time_remaining_seconds": max(0, (self.expires_at - datetime.now()).total_seconds()),
            "approval_message": self.approval_message,
            "category": self.tool_info.category
        }


class ToolApprovalService:
    """
    Manages tool call approvals.
    
    This service handles:
    - Creating approval requests for tools that require consent
    - Auto-approving tools based on user roles and settings
    - Tracking approval status
    - Notifying UI about pending approvals
    - Handling approval timeouts
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self._pending_approvals: Dict[str, ApprovalRequest] = {}
        self._approval_history: List[ToolCall] = []
        self._approval_callbacks: List[Callable] = []
        self._auto_approve_enabled: Dict[str, Dict[str, bool]] = {}  # user_id -> tool_name -> enabled
        self._approval_timeout_seconds = 300  # 5 minutes default
        
    async def request_approval(self, tool_call: ToolCall) -> ApprovalRequest:
        """
        Request approval for a tool call.
        
        This will either:
        1. Auto-approve if the user has auto-approval for this tool
        2. Create a pending approval request for UI interaction
        
        Args:
            tool_call: The tool call requiring approval
            
        Returns:
            ApprovalRequest with current status
        """
        tool = self.tool_registry.get_tool(tool_call.tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_call.tool_name}")
        
        # Check if auto-approval is enabled for this user/tool combination
        if self._should_auto_approve(tool_call):
            tool_call.approval_status = ToolApprovalStatus.AUTO_APPROVED
            tool_call.approved_at = datetime.now()
            tool_call.approved_by = "system"
            
            approval_request = ApprovalRequest(
                id=str(uuid.uuid4()),
                tool_call=tool_call,
                tool_info=tool,
                approval_message="Auto-approved based on user settings"
            )
            
            logger.info(f"Auto-approved tool call: {tool_call.tool_name} for user {tool_call.user_id}")
            return approval_request
        
        # Create pending approval request
        approval_request = ApprovalRequest(
            id=str(uuid.uuid4()),
            tool_call=tool_call,
            tool_info=tool,
            expires_at=datetime.now() + timedelta(seconds=self._approval_timeout_seconds)
        )
        
        self._pending_approvals[approval_request.id] = approval_request
        
        # Notify any registered callbacks (e.g., WebSocket to UI)
        await self._notify_approval_requested(approval_request)
        
        logger.info(f"Created approval request {approval_request.id} for tool: {tool_call.tool_name}")
        return approval_request
    
    async def approve_tool_call(self, approval_id: str, approved_by: str, message: Optional[str] = None) -> bool:
        """
        Approve a pending tool call.
        
        Args:
            approval_id: ID of the approval request
            approved_by: User who approved the request
            message: Optional approval message/reason
            
        Returns:
            True if approval was successful, False if request not found or expired
        """
        approval_request = self._pending_approvals.get(approval_id)
        if not approval_request:
            logger.warning(f"Approval request {approval_id} not found")
            return False
            
        if approval_request.is_expired():
            logger.warning(f"Approval request {approval_id} has expired")
            approval_request.tool_call.approval_status = ToolApprovalStatus.EXPIRED
            del self._pending_approvals[approval_id]
            return False
        
        # Update tool call with approval
        approval_request.tool_call.approval_status = ToolApprovalStatus.APPROVED
        approval_request.tool_call.approved_by = approved_by
        approval_request.tool_call.approved_at = datetime.now()
        approval_request.approval_message = message
        
        # Move to history
        self._approval_history.append(approval_request.tool_call)
        del self._pending_approvals[approval_id]
        
        # Notify callbacks
        await self._notify_approval_completed(approval_request)
        
        logger.info(f"Tool call approved: {approval_request.tool_call.tool_name} by {approved_by}")
        return True
    
    async def reject_tool_call(self, approval_id: str, rejected_by: str, reason: Optional[str] = None) -> bool:
        """
        Reject a pending tool call.
        
        Args:
            approval_id: ID of the approval request
            rejected_by: User who rejected the request
            reason: Optional rejection reason
            
        Returns:
            True if rejection was successful, False if request not found
        """
        approval_request = self._pending_approvals.get(approval_id)
        if not approval_request:
            logger.warning(f"Approval request {approval_id} not found")
            return False
        
        # Update tool call with rejection
        approval_request.tool_call.approval_status = ToolApprovalStatus.REJECTED
        approval_request.tool_call.approved_by = rejected_by
        approval_request.tool_call.approved_at = datetime.now()
        approval_request.approval_message = reason
        
        # Move to history
        self._approval_history.append(approval_request.tool_call)
        del self._pending_approvals[approval_id]
        
        # Notify callbacks
        await self._notify_approval_completed(approval_request)
        
        logger.info(f"Tool call rejected: {approval_request.tool_call.tool_name} by {rejected_by}")
        return True
    
    async def wait_for_approval(self, approval_id: str, timeout: Optional[float] = None) -> ToolApprovalStatus:
        """
        Wait for an approval request to be resolved.
        
        Args:
            approval_id: ID of the approval request
            timeout: Maximum time to wait in seconds
            
        Returns:
            Final approval status
        """
        start_time = datetime.now()
        timeout = timeout or self._approval_timeout_seconds
        
        while True:
            # Check if approval request still exists
            approval_request = self._pending_approvals.get(approval_id)
            if not approval_request:
                # Check history for completed approval
                for tool_call in reversed(self._approval_history):
                    if hasattr(tool_call, '_approval_id') and tool_call._approval_id == approval_id:
                        return tool_call.approval_status
                return ToolApprovalStatus.EXPIRED
            
            # Check if expired
            if approval_request.is_expired():
                approval_request.tool_call.approval_status = ToolApprovalStatus.EXPIRED
                del self._pending_approvals[approval_id]
                return ToolApprovalStatus.EXPIRED
            
            # Check timeout
            if (datetime.now() - start_time).total_seconds() > timeout:
                return ToolApprovalStatus.PENDING
            
            # Wait a bit before checking again
            await asyncio.sleep(0.5)
    
    def get_pending_approvals(self, user_id: Optional[str] = None, conversation_id: Optional[str] = None) -> List[ApprovalRequest]:
        """
        Get all pending approval requests.
        
        Args:
            user_id: Filter by user ID
            conversation_id: Filter by conversation ID
            
        Returns:
            List of pending approval requests
        """
        approvals = list(self._pending_approvals.values())
        
        # Remove expired approvals
        for approval in approvals:
            if approval.is_expired():
                del self._pending_approvals[approval.id]
        
        # Filter results
        if user_id:
            approvals = [a for a in approvals if a.tool_call.user_id == user_id]
        if conversation_id:
            approvals = [a for a in approvals if a.tool_call.conversation_id == conversation_id]
            
        return approvals
    
    def enable_auto_approval(self, user_id: str, tool_name: str, enabled: bool = True) -> None:
        """
        Enable or disable auto-approval for a specific user/tool combination.
        
        Args:
            user_id: User ID
            tool_name: Name of the tool
            enabled: Whether to enable auto-approval
        """
        if user_id not in self._auto_approve_enabled:
            self._auto_approve_enabled[user_id] = {}
        self._auto_approve_enabled[user_id][tool_name] = enabled
        
        logger.info(f"Auto-approval for {tool_name} {'enabled' if enabled else 'disabled'} for user {user_id}")
    
    def register_approval_callback(self, callback: Callable) -> None:
        """
        Register a callback to be notified of approval events.
        
        The callback will receive the ApprovalRequest object.
        """
        self._approval_callbacks.append(callback)
    
    def _should_auto_approve(self, tool_call: ToolCall) -> bool:
        """Check if a tool call should be auto-approved."""
        # Check user-specific auto-approval settings
        user_settings = self._auto_approve_enabled.get(tool_call.user_id, {})
        if tool_call.tool_name in user_settings:
            return user_settings[tool_call.tool_name]
        
        # Check tool's default auto-approval rules
        tool = self.tool_registry.get_tool(tool_call.tool_name)
        if tool and not tool.requires_approval:
            return True
            
        # Additional logic can be added here (e.g., based on user role)
        return False
    
    async def _notify_approval_requested(self, approval_request: ApprovalRequest) -> None:
        """Notify callbacks that an approval has been requested."""
        for callback in self._approval_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback("approval_requested", approval_request)
                else:
                    callback("approval_requested", approval_request)
            except Exception as e:
                logger.error(f"Error in approval callback: {e}")
    
    async def _notify_approval_completed(self, approval_request: ApprovalRequest) -> None:
        """Notify callbacks that an approval has been completed."""
        for callback in self._approval_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback("approval_completed", approval_request)
                else:
                    callback("approval_completed", approval_request)
            except Exception as e:
                logger.error(f"Error in approval callback: {e}")