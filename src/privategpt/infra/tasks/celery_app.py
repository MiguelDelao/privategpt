from __future__ import annotations

"""Celery application & tasks for background ingestion."""

from celery import Celery, current_task
from privategpt.shared.settings import settings  # type: ignore
from privategpt.infra.tasks.service_factory import build_rag_service
from privategpt.core.domain.document import DocumentStatus
from privategpt.infra.database.async_session import AsyncSessionLocal
from privategpt.infra.database.document_repository import SqlDocumentRepository
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

logger = logging.getLogger(__name__)

app = Celery(
    "rag",
    broker=settings.redis_url or "redis://redis:6379/0",
    backend=settings.redis_url or "redis://redis:6379/1",
)


@app.task(name="ingest_document")
def ingest_document_task(doc_id: int, file_path: str, title: str, text: str):
    """Background ingestion task – split, embed, vector-store, save chunks."""

    async def _run():
        async with AsyncSessionLocal() as session:  # type: AsyncSession
            repo = SqlDocumentRepository(session)
            rag = build_rag_service(session)

            try:
                await rag.ingest_document(title, file_path, text)
                doc = await repo.get(doc_id)
                if doc:
                    doc.status = DocumentStatus.COMPLETE
                    await repo.update(doc)
            except Exception as exc:  # noqa: BLE001
                doc = await repo.get(doc_id)
                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.error = str(exc)
                    await repo.update(doc)
                raise

    asyncio.run(_run())


@app.task(name="save_assistant_message")
def save_assistant_message_task(
    conversation_id: str,
    message_id: str,
    content: str,
    raw_content: Optional[str] = None,
    thinking_content: Optional[str] = None,
    token_count: Optional[int] = None,
    data: Optional[Dict[str, Any]] = None
):
    """Save assistant message after streaming completes."""
    
    async def _run():
        from privategpt.infra.database.message_repository import SqlMessageRepository
        from privategpt.infra.database.conversation_repository import SqlConversationRepository
        from privategpt.core.domain.message import Message
        
        async with AsyncSessionLocal() as session:
            message_repo = SqlMessageRepository(session)
            conversation_repo = SqlConversationRepository(session)
            
            try:
                # Create the assistant message
                assistant_message = Message(
                    id=message_id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=content,
                    raw_content=raw_content,
                    thinking_content=thinking_content,
                    token_count=token_count,
                    data=data or {},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                # Save to database
                await message_repo.create(assistant_message)
                
                # Update conversation token count if provided
                if token_count and data and "total_tokens" in data:
                    conversation = await conversation_repo.get(conversation_id)
                    if conversation:
                        conversation.add_message_tokens(data["total_tokens"])
                        conversation.updated_at = datetime.utcnow()
                        await conversation_repo.update(conversation)
                
                logger.info(f"Saved assistant message {message_id} for conversation {conversation_id}")
                
            except Exception as e:
                logger.error(f"Failed to save assistant message: {e}")
                raise
    
    asyncio.run(_run())


@app.task(name="cleanup_expired_stream_sessions")
def cleanup_expired_stream_sessions_task():
    """Periodic task to clean up expired stream sessions from Redis."""
    
    async def _run():
        from privategpt.infra.cache.redis_client import get_redis_client
        
        redis_client = get_redis_client()
        try:
            await redis_client.connect()
            # Redis automatically expires keys with TTL, but we can add
            # additional cleanup logic here if needed
            logger.info("Stream session cleanup task completed")
        finally:
            await redis_client.close()
    
    asyncio.run(_run()) 