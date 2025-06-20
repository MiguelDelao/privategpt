from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from privategpt.core.domain.message import Message


class MessageRepository(ABC):
    """Repository interface for message persistence"""
    
    @abstractmethod
    async def get(self, message_id: str) -> Optional[Message]:
        """Get message by ID"""
        pass
    
    @abstractmethod
    async def get_by_conversation(self, conversation_id: str, limit: int = 100, offset: int = 0) -> List[Message]:
        """Get messages for a specific conversation"""
        pass
    
    @abstractmethod
    async def create(self, message: Message) -> Message:
        """Create a new message"""
        pass
    
    @abstractmethod
    async def update(self, message: Message) -> Message:
        """Update an existing message"""
        pass
    
    @abstractmethod
    async def delete(self, message_id: str) -> bool:
        """Delete a message"""
        pass
    
    @abstractmethod
    async def get_latest_by_conversation(self, conversation_id: str, count: int = 10) -> List[Message]:
        """Get the latest N messages from a conversation"""
        pass