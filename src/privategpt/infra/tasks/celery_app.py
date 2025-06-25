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


@app.task(name="ingest_document", bind=True)
def ingest_document_task(self, doc_id: int, file_path: str, title: str, text: str):
    """Background ingestion task – split, embed, vector-store, save chunks."""
    # Use synchronous implementation to avoid asyncio issues with Celery
    from privategpt.infra.tasks.celery_sync import process_document_sync
    process_document_sync(doc_id, file_path, title, text)


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
    
    from privategpt.infra.database.sync_session import get_sync_session_context
    from privategpt.infra.database.sync_repositories import SyncMessageRepository, SyncConversationRepository
    from privategpt.core.domain.message import Message
    
    with get_sync_session_context() as session:
        message_repo = SyncMessageRepository(session)
        conversation_repo = SyncConversationRepository(session)
        
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
            message_repo.create(assistant_message)
            
            # Update conversation token count if provided
            if token_count and data and "total_tokens" in data:
                conversation = conversation_repo.get(conversation_id)
                if conversation:
                    conversation.add_message_tokens(data["total_tokens"])
                    conversation.updated_at = datetime.utcnow()
                    conversation_repo.update(conversation)
            
            logger.info(f"Saved assistant message {message_id} for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to save assistant message: {e}")
            raise


@app.task(name="cleanup_expired_stream_sessions")
def cleanup_expired_stream_sessions_task():
    """Periodic task to clean up expired stream sessions from Redis."""
    
    # Note: Redis automatically expires keys with TTL
    # This task can be used for additional cleanup if needed
    logger.info("Stream session cleanup task completed") 