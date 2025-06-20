from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from privategpt.core.domain.message import Message as DomainMessage
from privategpt.core.ports.message_repository import MessageRepository
from privategpt.infra.database.models import Message, MessageRole


class SqlMessageRepository(MessageRepository):
    """SQLAlchemy implementation of message repository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get(self, message_id: str) -> Optional[DomainMessage]:
        """Get message by ID"""
        stmt = (
            select(Message)
            .options(selectinload(Message.tool_calls))
            .where(Message.id == message_id)
        )
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()
        
        if not message:
            return None
            
        return self._to_domain(message)
    
    async def get_by_conversation(self, conversation_id: str, limit: int = 100, offset: int = 0) -> List[DomainMessage]:
        """Get messages for a specific conversation"""
        stmt = (
            select(Message)
            .options(selectinload(Message.tool_calls))
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        messages = result.scalars().all()
        
        return [self._to_domain(msg) for msg in messages]
    
    async def create(self, message: DomainMessage) -> DomainMessage:
        """Create a new message"""
        db_message = Message(
            id=message.id,
            conversation_id=message.conversation_id,
            role=MessageRole(message.role),
            content=message.content,
            raw_content=message.raw_content,
            token_count=message.token_count,
            data=message.data,
            created_at=message.created_at,
            updated_at=message.updated_at
        )
        
        self.session.add(db_message)
        await self.session.commit()
        await self.session.refresh(db_message)
        
        return self._to_domain(db_message)
    
    async def update(self, message: DomainMessage) -> DomainMessage:
        """Update an existing message"""
        stmt = select(Message).where(Message.id == message.id)
        result = await self.session.execute(stmt)
        db_message = result.scalar_one_or_none()
        
        if not db_message:
            raise ValueError(f"Message {message.id} not found")
        
        # Update fields
        db_message.content = message.content
        db_message.raw_content = message.raw_content
        db_message.token_count = message.token_count
        db_message.data = message.data
        db_message.updated_at = message.updated_at
        
        await self.session.commit()
        await self.session.refresh(db_message)
        
        return self._to_domain(db_message)
    
    async def delete(self, message_id: str) -> bool:
        """Delete a message"""
        stmt = select(Message).where(Message.id == message_id)
        result = await self.session.execute(stmt)
        db_message = result.scalar_one_or_none()
        
        if not db_message:
            return False
        
        await self.session.delete(db_message)
        await self.session.commit()
        return True
    
    async def get_latest_by_conversation(self, conversation_id: str, count: int = 10) -> List[DomainMessage]:
        """Get the latest N messages from a conversation"""
        stmt = (
            select(Message)
            .options(selectinload(Message.tool_calls))
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(count)
        )
        result = await self.session.execute(stmt)
        messages = result.scalars().all()
        
        # Reverse to get chronological order
        return [self._to_domain(msg) for msg in reversed(messages)]
    
    def _to_domain(self, db_message: Message) -> DomainMessage:
        """Convert database model to domain model"""
        from privategpt.core.domain.tool_call import ToolCall as DomainToolCall
        
        tool_calls = []
        if hasattr(db_message, 'tool_calls') and db_message.tool_calls:
            tool_calls = [
                DomainToolCall(
                    id=tc.id,
                    message_id=tc.message_id,
                    name=tc.name,
                    parameters=tc.parameters or {},
                    result=tc.result,
                    error_message=tc.error_message,
                    status=tc.status.value,
                    execution_time_ms=tc.execution_time_ms,
                    data=tc.data or {},
                    created_at=tc.created_at,
                    updated_at=tc.updated_at
                )
                for tc in db_message.tool_calls
            ]
        
        return DomainMessage(
            id=db_message.id,
            conversation_id=db_message.conversation_id,
            role=db_message.role.value,
            content=db_message.content,
            raw_content=db_message.raw_content,
            token_count=db_message.token_count,
            data=db_message.data or {},
            tool_calls=tool_calls,
            created_at=db_message.created_at,
            updated_at=db_message.updated_at
        )