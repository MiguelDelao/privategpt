from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from privategpt.core.domain.tool_call import ToolCall


class ToolCallRepository(ABC):
    """Repository interface for tool call persistence"""
    
    @abstractmethod
    async def get(self, tool_call_id: str) -> Optional[ToolCall]:
        """Get tool call by ID"""
        pass
    
    @abstractmethod
    async def get_by_message(self, message_id: str) -> List[ToolCall]:
        """Get tool calls for a specific message"""
        pass
    
    @abstractmethod
    async def create(self, tool_call: ToolCall) -> ToolCall:
        """Create a new tool call"""
        pass
    
    @abstractmethod
    async def update(self, tool_call: ToolCall) -> ToolCall:
        """Update an existing tool call"""
        pass
    
    @abstractmethod
    async def delete(self, tool_call_id: str) -> bool:
        """Delete a tool call"""
        pass
    
    @abstractmethod
    async def get_pending(self, limit: int = 50) -> List[ToolCall]:
        """Get pending tool calls"""
        pass
    
    @abstractmethod
    async def get_by_status(self, status: str, limit: int = 100) -> List[ToolCall]:
        """Get tool calls by status"""
        pass