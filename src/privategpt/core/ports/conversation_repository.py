from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from privategpt.core.domain.conversation import Conversation


class ConversationRepository(ABC):
    """Repository interface for conversation persistence"""
    
    @abstractmethod
    async def get(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        pass
    
    @abstractmethod
    async def get_by_user(self, user_id: int, limit: int = 50, offset: int = 0) -> List[Conversation]:
        """Get conversations for a specific user"""
        pass
    
    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        """Create a new conversation"""
        pass
    
    @abstractmethod
    async def update(self, conversation: Conversation) -> Conversation:
        """Update an existing conversation"""
        pass
    
    @abstractmethod
    async def delete(self, conversation_id: str, hard_delete: bool = False) -> bool:
        """Delete a conversation"""
        pass
    
    @abstractmethod
    async def archive(self, conversation_id: str) -> bool:
        """Archive a conversation"""
        pass
    
    @abstractmethod
    async def search(self, user_id: int, query: str, limit: int = 20) -> List[Conversation]:
        """Search conversations by title or content"""
        pass