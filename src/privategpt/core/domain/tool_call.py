from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass(slots=True)
class ToolCall:
    """Domain model for tool/function call within a message"""
    
    id: str
    message_id: str
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    error_message: Optional[str] = None
    status: str = "pending"  # "pending", "running", "completed", "failed", "cancelled"
    execution_time_ms: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def mark_running(self) -> None:
        """Mark tool call as running"""
        self.status = "running"
        self.updated_at = datetime.utcnow()
    
    def mark_completed(self, result: str, execution_time_ms: Optional[int] = None) -> None:
        """Mark tool call as completed with result"""
        self.status = "completed"
        self.result = result
        self.execution_time_ms = execution_time_ms
        self.updated_at = datetime.utcnow()
    
    def mark_failed(self, error_message: str, execution_time_ms: Optional[int] = None) -> None:
        """Mark tool call as failed with error"""
        self.status = "failed"
        self.error_message = error_message
        self.execution_time_ms = execution_time_ms
        self.updated_at = datetime.utcnow()
    
    def mark_cancelled(self) -> None:
        """Mark tool call as cancelled"""
        self.status = "cancelled"
        self.updated_at = datetime.utcnow()
    
    def is_pending(self) -> bool:
        """Check if tool call is pending execution"""
        return self.status == "pending"
    
    def is_running(self) -> bool:
        """Check if tool call is currently running"""
        return self.status == "running"
    
    def is_completed(self) -> bool:
        """Check if tool call completed successfully"""
        return self.status == "completed"
    
    def is_failed(self) -> bool:
        """Check if tool call failed"""
        return self.status == "failed"
    
    def is_finished(self) -> bool:
        """Check if tool call is finished (completed, failed, or cancelled)"""
        return self.status in ["completed", "failed", "cancelled"]