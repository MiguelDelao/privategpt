from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

from privategpt.core.domain.tool_call import ToolCall


@dataclass(slots=True)
class Message:
    """Domain model for individual message in conversation"""
    
    id: str
    conversation_id: str
    role: str  # "user", "assistant", "system", "tool"
    content: str  # Processed content for UI (thinking stripped)
    raw_content: Optional[str] = None  # Original unprocessed content with thinking
    thinking_content: Optional[str] = None  # Extracted thinking content for debug
    token_count: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[ToolCall] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def add_tool_call(self, tool_call: ToolCall) -> None:
        """Add a tool call to this message"""
        self.tool_calls.append(tool_call)
        self.updated_at = datetime.utcnow()
    
    def has_tool_calls(self) -> bool:
        """Check if message contains tool calls"""
        return len(self.tool_calls) > 0
    
    def get_pending_tool_calls(self) -> List[ToolCall]:
        """Get all pending tool calls"""
        return [tc for tc in self.tool_calls if tc.status == "pending"]
    
    def get_completed_tool_calls(self) -> List[ToolCall]:
        """Get all completed tool calls"""
        return [tc for tc in self.tool_calls if tc.status == "completed"]
    
    def get_failed_tool_calls(self) -> List[ToolCall]:
        """Get all failed tool calls"""
        return [tc for tc in self.tool_calls if tc.status == "failed"]
    
    def is_from_user(self) -> bool:
        """Check if message is from user"""
        return self.role == "user"
    
    def is_from_assistant(self) -> bool:
        """Check if message is from assistant"""
        return self.role == "assistant"
    
    def is_system_message(self) -> bool:
        """Check if message is system message"""
        return self.role == "system"