from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from privategpt.core.domain.conversation import Conversation as DomainConversation
from privategpt.core.ports.conversation_repository import ConversationRepository
from privategpt.infra.database.models import Conversation, Message, ConversationStatus


class SqlConversationRepository(ConversationRepository):
    """SQLAlchemy implementation of conversation repository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get(self, conversation_id: str) -> Optional[DomainConversation]:
        """Get conversation by ID"""
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        result = await self.session.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return None
            
        return self._to_domain(conversation)
    
    async def get_by_user(self, user_id: int, limit: int = 50, offset: int = 0) -> List[DomainConversation]:
        """Get conversations for a specific user"""
        stmt = (
            select(Conversation)
            .where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.status != ConversationStatus.DELETED
                )
            )
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        conversations = result.scalars().all()
        
        return [self._to_domain(conv) for conv in conversations]
    
    async def create(self, conversation: DomainConversation) -> DomainConversation:
        """Create a new conversation"""
        db_conversation = Conversation(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            status=conversation.status,
            model_name=conversation.model_name,
            system_prompt=conversation.system_prompt,
            data=conversation.data,
            total_tokens=conversation.total_tokens,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )
        
        try:
            self.session.add(db_conversation)
            await self.session.commit()
            await self.session.refresh(db_conversation)
            return self._to_domain(db_conversation)
        except Exception as e:
            await self.session.rollback()
            raise Exception(f"Failed to create conversation: {e}")
    
    async def update(self, conversation: DomainConversation) -> DomainConversation:
        """Update an existing conversation"""
        stmt = select(Conversation).where(Conversation.id == conversation.id)
        result = await self.session.execute(stmt)
        db_conversation = result.scalar_one_or_none()
        
        if not db_conversation:
            raise ValueError(f"Conversation {conversation.id} not found")
        
        # Update fields
        db_conversation.title = conversation.title
        db_conversation.status = conversation.status
        db_conversation.model_name = conversation.model_name
        db_conversation.system_prompt = conversation.system_prompt
        db_conversation.data = conversation.data
        db_conversation.total_tokens = conversation.total_tokens
        db_conversation.updated_at = conversation.updated_at
        
        try:
            await self.session.commit()
            await self.session.refresh(db_conversation)
            return self._to_domain(db_conversation)
        except Exception as e:
            await self.session.rollback()
            raise Exception(f"Failed to update conversation: {e}")
    
    async def delete(self, conversation_id: str) -> bool:
        """Delete a conversation (soft delete by setting status)"""
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.session.execute(stmt)
        db_conversation = result.scalar_one_or_none()
        
        if not db_conversation:
            return False
        
        db_conversation.status = ConversationStatus.DELETED
        await self.session.commit()
        return True
    
    async def archive(self, conversation_id: str) -> bool:
        """Archive a conversation"""
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.session.execute(stmt)
        db_conversation = result.scalar_one_or_none()
        
        if not db_conversation:
            return False
        
        db_conversation.status = ConversationStatus.ARCHIVED
        await self.session.commit()
        return True
    
    async def search(self, user_id: int, query: str, limit: int = 20) -> List[DomainConversation]:
        """Search conversations by title or content"""
        # Search in conversation titles and message content
        stmt = (
            select(Conversation)
            .outerjoin(Message)
            .where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.status != ConversationStatus.DELETED,
                    or_(
                        Conversation.title.ilike(f"%{query}%"),
                        Message.content.ilike(f"%{query}%")
                    )
                )
            )
            .distinct()
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        conversations = result.scalars().all()
        
        return [self._to_domain(conv) for conv in conversations]
    
    def _to_domain(self, db_conversation: Conversation) -> DomainConversation:
        """Convert database model to domain model"""
        from privategpt.core.domain.message import Message as DomainMessage
        
        messages = []
        if hasattr(db_conversation, 'messages') and db_conversation.messages:
            messages = [
                DomainMessage(
                    id=msg.id,
                    conversation_id=msg.conversation_id,
                    role=msg.role.value,
                    content=msg.content,
                    raw_content=msg.raw_content,
                    token_count=msg.token_count,
                    data=msg.data or {},
                    created_at=msg.created_at,
                    updated_at=msg.updated_at
                )
                for msg in db_conversation.messages
            ]
        
        return DomainConversation(
            id=db_conversation.id,
            user_id=db_conversation.user_id,
            title=db_conversation.title,
            status=db_conversation.status.value,
            model_name=db_conversation.model_name,
            system_prompt=db_conversation.system_prompt,
            data=db_conversation.data or {},
            messages=messages,
            total_tokens=db_conversation.total_tokens,
            created_at=db_conversation.created_at,
            updated_at=db_conversation.updated_at
        )