from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.orm import Session, selectinload

from privategpt.core.domain.message import Message as DomainMessage
from privategpt.core.domain.conversation import Conversation as DomainConversation
from privategpt.infra.database.models import Message, MessageRole, Conversation


class SyncMessageRepository:
    """Synchronous SQLAlchemy implementation of message repository for Celery tasks"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, message: DomainMessage) -> DomainMessage:
        """Create a new message"""
        db_message = Message(
            id=message.id,
            conversation_id=message.conversation_id,
            role=MessageRole(message.role),
            content=message.content,
            raw_content=message.raw_content,
            thinking_content=message.thinking_content,
            token_count=message.token_count,
            data=message.data,
            created_at=message.created_at,
            updated_at=message.updated_at
        )
        
        self.session.add(db_message)
        self.session.commit()
        self.session.refresh(db_message)
        
        return self._to_domain(db_message)
    
    def _to_domain(self, db_message: Message) -> DomainMessage:
        """Convert database model to domain model"""
        return DomainMessage(
            id=db_message.id,
            conversation_id=db_message.conversation_id,
            role=db_message.role.value,
            content=db_message.content,
            raw_content=db_message.raw_content,
            thinking_content=db_message.thinking_content,
            token_count=db_message.token_count,
            data=db_message.data or {},
            tool_calls=[],  # Not loading tool calls in sync version for simplicity
            created_at=db_message.created_at,
            updated_at=db_message.updated_at
        )


class SyncConversationRepository:
    """Synchronous SQLAlchemy implementation of conversation repository for Celery tasks"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get(self, conversation_id: str) -> Optional[DomainConversation]:
        """Get conversation by ID"""
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = self.session.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return None
            
        return self._to_domain(conversation)
    
    def update(self, conversation: DomainConversation) -> DomainConversation:
        """Update an existing conversation"""
        stmt = select(Conversation).where(Conversation.id == conversation.id)
        result = self.session.execute(stmt)
        db_conversation = result.scalar_one_or_none()
        
        if not db_conversation:
            raise ValueError(f"Conversation {conversation.id} not found")
        
        # Update fields
        db_conversation.title = conversation.title
        db_conversation.total_tokens = conversation.total_tokens
        db_conversation.data = conversation.data
        db_conversation.updated_at = conversation.updated_at
        
        self.session.commit()
        self.session.refresh(db_conversation)
        
        return self._to_domain(db_conversation)
    
    def _to_domain(self, db_conversation: Conversation) -> DomainConversation:
        """Convert database model to domain model"""
        return DomainConversation(
            id=db_conversation.id,
            user_id=db_conversation.user_id,
            title=db_conversation.title,
            model_name=db_conversation.model_name,
            total_tokens=db_conversation.total_tokens,
            is_archived=db_conversation.is_archived,
            data=db_conversation.data or {},
            created_at=db_conversation.created_at,
            updated_at=db_conversation.updated_at
        )