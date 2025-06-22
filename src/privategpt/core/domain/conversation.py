from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from privategpt.core.domain.message import Message


@dataclass(slots=True)
class Conversation:
    """Domain model for conversation/chat session"""
    
    id: str
    user_id: int
    title: str
    status: str = "active"
    model_name: Optional[str] = None
    system_prompt: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    messages: List[Message] = field(default_factory=list)
    total_tokens: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def add_message(self, message: Message) -> None:
        """Add a message to the conversation"""
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
    
    def add_message_tokens(self, tokens: int) -> None:
        """Add tokens to the conversation total"""
        self.total_tokens += tokens
    
    def get_message_count(self) -> int:
        """Get total number of messages in conversation"""
        return len(self.messages)
    
    def get_total_tokens(self) -> int:
        """Get total tokens used in conversation (from stored total)"""
        return self.total_tokens
    
    def get_last_message(self) -> Optional[Message]:
        """Get the most recent message"""
        return self.messages[-1] if self.messages else None
    
    def get_messages_by_role(self, role: str) -> List[Message]:
        """Get all messages with specific role"""
        return [msg for msg in self.messages if msg.role == role]