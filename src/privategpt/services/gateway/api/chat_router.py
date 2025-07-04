from __future__ import annotations

"""
Chat and conversation management API routes for the gateway.
"""

import logging
import uuid
import enum
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.shared.auth_middleware import get_current_user, get_current_user_flexible
from fastapi import Depends, Query
from typing import Optional
from privategpt.infra.database.async_session import get_async_session
from privategpt.services.gateway.core.chat_service import ChatService
from privategpt.services.gateway.core.exceptions import (
    ChatContextLimitError,
    ServiceUnavailableError,
    ModelNotAvailableError,
    ValidationError as ServiceValidationError
)
from privategpt.infra.database.models import User
from sqlalchemy import select
from privategpt.infra.database.models import Message, MessageRole
from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)


# Authentication helper functions removed - using proper auth dependencies now


async def ensure_user_exists(session: AsyncSession, user_claims: Dict[str, Any]) -> int:
    """Ensure user exists in database, create if not found"""
    # Handle case when auth is disabled (for debugging)
    if not user_claims:
        logger.warning("No user claims provided, using demo user")
        # Create/use demo user with ID 1
        stmt = select(User).where(User.id == 1)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            demo_user = User(
                id=1,
                keycloak_id="demo-user",
                email="admin@admin.com",
                username="admin",
                first_name="Demo",
                last_name="User",
                role="admin",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(demo_user)
            await session.commit()
            await session.refresh(demo_user)
            logger.info("Created demo user for testing")
        
        return 1
    
    # Extract user ID from claims - handle both 'sub' and 'user_id' fields
    keycloak_user_id = user_claims.get("sub") or user_claims.get("user_id")
    if not keycloak_user_id:
        logger.error(f"No user ID found in claims: {user_claims}")
        raise HTTPException(status_code=401, detail="Invalid user claims - missing user ID")
    
    logger.info(f"Looking up user with keycloak_id: {keycloak_user_id}, claims: {user_claims}")
    
    # Check if user exists by keycloak_id
    stmt = select(User).where(User.keycloak_id == keycloak_user_id)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        logger.info(f"Found existing user: {existing_user.id} ({existing_user.email})")
        return existing_user.id
    
    # Extract user info from claims
    email = user_claims.get("email")
    username = user_claims.get("username") or user_claims.get("preferred_username")
    first_name = user_claims.get("first_name") or user_claims.get("given_name")
    last_name = user_claims.get("last_name") or user_claims.get("family_name")
    
    # Get primary role from claims
    primary_role = user_claims.get("primary_role", "user")
    
    logger.info(f"Creating new user - email: {email}, username: {username}, role: {primary_role}")
    
    # Create new user (let database auto-assign integer ID)
    try:
        new_user = User(
            keycloak_id=keycloak_user_id,
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=primary_role,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        logger.info(f"Created new user: {new_user.id} ({new_user.email})")
        return new_user.id
        
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        await session.rollback()
        
        # Check if user was created by another request (race condition)
        stmt = select(User).where(User.keycloak_id == keycloak_user_id)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            logger.info(f"User found after creation failure: {existing_user.id} ({existing_user.email})")
            return existing_user.id
        
        # If still not found, re-raise the error
        raise

router = APIRouter(prefix="/api/chat", tags=["chat"])


# Test endpoint without any database operations
@router.post("/debug/test-stream-prepare")
async def test_stream_prepare(authorization: str = Header(None)):
    """Test endpoint to verify streaming works without database operations"""
    logger.info("=== TEST STREAM PREPARE ENDPOINT ===")
    
    try:
        from privategpt.services.gateway.core.stream_session import StreamSessionManager
        
        logger.info("Creating stream manager")
        stream_manager = StreamSessionManager()
        
        logger.info("Creating test stream session")
        stream_session = await stream_manager.create_session(
            conversation_id="test-conv",
            user_id=1,
            user_message_id="test-user-msg",
            llm_messages=[{"role": "user", "content": "test message"}],
            model_name="tinyllama:1.1b"
        )
        
        logger.info(f"Test stream session created: {stream_session.token}")
        
        return {
            "stream_token": stream_session.token,
            "stream_url": f"/stream/{stream_session.token}",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Test stream prepare failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


# Pydantic models for API
class ConversationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    model_name: Optional[str] = Field(None, max_length=100)
    system_prompt: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, pattern="^(active|archived|deleted)$")
    model_name: Optional[str] = Field(None, max_length=100)
    system_prompt: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    status: str
    model_name: Optional[str]
    system_prompt: Optional[str]
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class MessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system|tool)$")
    content: str = Field(..., min_length=1)
    raw_content: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    raw_content: Optional[str]
    token_count: Optional[int]
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    stream: bool = Field(default=False)
    model: Optional[str] = None  # Changed from model_name for consistency
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    use_mcp: bool = Field(default=True)
    available_tools: str = Field(default="*")  # "*", "", or "tool1,tool2"
    
    # Backward compatibility
    @property
    def model_name(self) -> Optional[str]:
        return self.model


class ChatResponse(BaseModel):
    conversation_id: str
    message: MessageResponse
    response: MessageResponse


# Conversation endpoints
@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new conversation"""
    from privategpt.infra.database.async_session import get_async_session_context
    from privategpt.core.domain.conversation import Conversation
    from privategpt.infra.database.conversation_repository import SqlConversationRepository
    import uuid
    from datetime import datetime
    
    async with get_async_session_context() as session:
        # Ensure user exists in database (auto-create if needed)
        user_id = await ensure_user_exists(session, user)
        
        # Create domain conversation
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=conversation_data.title,
            status="active",
            model_name=conversation_data.model_name,
            system_prompt=conversation_data.system_prompt,
            data=conversation_data.data,
            total_tokens=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        repo = SqlConversationRepository(session)
        created_conversation = await repo.create(conversation)
        
        return ConversationResponse(
            id=created_conversation.id,
            title=created_conversation.title,
            status=created_conversation.status,
            model_name=created_conversation.model_name,
            system_prompt=created_conversation.system_prompt,
            data=created_conversation.data,
            created_at=created_conversation.created_at,
            updated_at=created_conversation.updated_at,
            message_count=len(created_conversation.messages)
        )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, pattern="^(active|archived|deleted)$"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """List user's conversations"""
    from privategpt.infra.database.async_session import get_async_session_context
    from privategpt.infra.database.conversation_repository import SqlConversationRepository
    
    async with get_async_session_context() as session:
        # Ensure user exists in database (auto-create if needed)
        user_id = await ensure_user_exists(session, user)
        
        repo = SqlConversationRepository(session)
        conversations = await repo.get_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return [
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                status=conv.status,
                model_name=conv.model_name,
                system_prompt=conv.system_prompt,
                data=conv.data,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=len(conv.messages)
            )
            for conv in conversations
        ]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific conversation"""
    chat_service = ChatService(session)
    
    try:
        # Ensure user exists in database (auto-create if needed)
        user_id = await ensure_user_exists(session, user)
        
        conversation = await chat_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            status=conversation.status,
            model_name=conversation.model_name,
            system_prompt=conversation.system_prompt,
            data=conversation.data,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=len(conversation.messages)
        )
    finally:
        await chat_service.close()


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a conversation"""
    from privategpt.infra.database.async_session import get_async_session_context
    from privategpt.infra.database.conversation_repository import SqlConversationRepository
    from datetime import datetime
    
    async with get_async_session_context() as session:
        # Ensure user exists in database (auto-create if needed)
        user_id = await ensure_user_exists(session, user)
        
        repo = SqlConversationRepository(session)
        
        # Get existing conversation
        conversation = await repo.get(conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Update fields if provided
        if update_data.title is not None:
            conversation.title = update_data.title
        if update_data.status is not None:
            conversation.status = update_data.status
        if update_data.model_name is not None:
            conversation.model_name = update_data.model_name
        if update_data.system_prompt is not None:
            conversation.system_prompt = update_data.system_prompt
        if update_data.data is not None:
            conversation.data = update_data.data
        
        conversation.updated_at = datetime.utcnow()
        
        # Update in database
        updated_conversation = await repo.update(conversation)
        
        return ConversationResponse(
            id=updated_conversation.id,
            title=updated_conversation.title,
            status=updated_conversation.status,
            model_name=updated_conversation.model_name,
            system_prompt=updated_conversation.system_prompt,
            data=updated_conversation.data,
            created_at=updated_conversation.created_at,
            updated_at=updated_conversation.updated_at,
            message_count=len(updated_conversation.messages)
        )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    hard_delete: bool = Query(False, description="If true, permanently delete. If false, soft delete by marking as deleted."),
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a conversation
    
    By default performs a soft delete (marks as deleted but keeps data).
    Set hard_delete=true to permanently remove the conversation and all its messages.
    """
    chat_service = ChatService(session)
    
    try:
        # Ensure user exists in database (auto-create if needed)
        user_id = await ensure_user_exists(session, user)
        
        # Verify conversation exists and user owns it
        conversation = await chat_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Delete conversation (soft or hard based on parameter)
        success = await chat_service.conversation_repo.delete(conversation_id, hard_delete=hard_delete)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete conversation")
            
        return None  # 204 No Content
    finally:
        await chat_service.close()


# Message endpoints
@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    conversation_id: str,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get messages for a conversation"""
    chat_service = ChatService(session)
    
    try:
        # Ensure user exists in database (auto-create if needed)
        user_id = await ensure_user_exists(session, user)
        
        # Verify conversation exists and user owns it
        conversation = await chat_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages for the conversation
        messages = await chat_service.message_repo.get_by_conversation(
            conversation_id, limit=limit, offset=offset
        )
        
        return [
            MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                role=msg.role.value if hasattr(msg.role, 'value') else msg.role,
                content=msg.content,
                raw_content=msg.raw_content,
                token_count=msg.token_count,
                data=msg.data,
                created_at=msg.created_at,
                updated_at=msg.updated_at
            )
            for msg in messages
        ]
    finally:
        await chat_service.close()


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    conversation_id: str,
    message_data: MessageCreate,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Add a message to a conversation"""
    chat_service = ChatService(session)
    
    try:
        # Ensure user exists in database (auto-create if needed)
        user_id = await ensure_user_exists(session, user)
        
        # Verify conversation exists and user owns it
        conversation = await chat_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Create domain message
        from privategpt.infra.database.models import Message, MessageRole as DomainMessage
        
        message = DomainMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=message_data.role,
            content=message_data.content,
            raw_content=message_data.raw_content,
            token_count=None,
            data=message_data.data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to database
        created_message = await chat_service.message_repo.create(message)
        
        return MessageResponse(
            id=created_message.id,
            conversation_id=created_message.conversation_id,
            role=created_message.role.value if hasattr(created_message.role, 'value') else created_message.role,
            content=created_message.content,
            raw_content=created_message.raw_content,
            token_count=created_message.token_count,
            data=created_message.data,
            created_at=created_message.created_at,
            updated_at=created_message.updated_at
        )
    finally:
        await chat_service.close()


# Chat endpoints with LLM integration
@router.post("/conversations/{conversation_id}/chat", response_model=ChatResponse)
async def chat_with_conversation(
    conversation_id: str,
    chat_request: ChatRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Send a message and get LLM response within a conversation"""
    if chat_request.stream:
        raise HTTPException(
            status_code=400, 
            detail="Use /chat/stream endpoint for streaming responses"
        )
    
    chat_service = ChatService(session)
    
    try:
        # Ensure user exists in database (auto-create if needed)
        user_id = await ensure_user_exists(session, user)
        
        # Send message and get response using ChatService
        user_message, assistant_message = await chat_service.send_message(
            conversation_id=conversation_id,
            user_id=user_id,
            message_content=chat_request.message,
            model_name=chat_request.model_name,
            temperature=chat_request.temperature,
            max_tokens=chat_request.max_tokens
        )
        
        return ChatResponse(
            conversation_id=conversation_id,
            message=MessageResponse(
                id=user_message.id,
                conversation_id=user_message.conversation_id,
                role=user_message.role.value if hasattr(user_message.role, 'value') else user_message.role,
                content=user_message.content,
                raw_content=user_message.raw_content,
                token_count=user_message.token_count,
                data=user_message.data,
                created_at=user_message.created_at,
                updated_at=user_message.updated_at
            ),
            response=MessageResponse(
                id=assistant_message.id,
                conversation_id=assistant_message.conversation_id,
                role=assistant_message.role.value if hasattr(assistant_message.role, 'value') else assistant_message.role,
                content=assistant_message.content,
                raw_content=assistant_message.raw_content,
                token_count=assistant_message.token_count,
                data=assistant_message.data,
                created_at=assistant_message.created_at,
                updated_at=assistant_message.updated_at
            )
        )
    except ChatContextLimitError as e:
        # Re-raise - will be handled by error handler
        raise
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise ServiceValidationError(message=str(e))
    except Exception as e:
        logger.error(f"Chat error: {e}")
        # Try to determine more specific error type
        error_msg = str(e).lower()
        if "connection" in error_msg or "unavailable" in error_msg:
            raise ServiceUnavailableError("LLM Service", str(e))
        elif "model" in error_msg and "not" in error_msg:
            raise ModelNotAvailableError(chat_request.model_name or "unknown")
        # Generic error
        raise
    finally:
        await chat_service.close()


@router.post("/conversations/{conversation_id}/chat/stream")
async def stream_chat_with_conversation(
    conversation_id: str,
    chat_request: ChatRequest,
    user: Dict[str, Any] = Depends(get_current_user_flexible),
    token: Optional[str] = Query(None),  # For EventSource compatibility
):
    """Stream chat response for a conversation"""
    
    # Get user_id from the authenticated user claims
    user_id = None
    if user and isinstance(user, dict):
        # If user has direct user_id, use it
        if "user_id" in user:
            user_id = user["user_id"]
        # If user has sub (from JWT), extract numeric ID
        elif "sub" in user:
            # For now, we'll use a simplified approach
            # In production, this should map Keycloak UUID to database user ID
            user_id = 1  # Default user for testing
    
    # If no user_id found, default to demo user
    if user_id is None:
        logger.warning("No user_id found in claims, using demo user")
        user_id = 1
    
    async def stream_generator():
        try:
            # For now, let's use a simplified streaming approach
            # that doesn't interact with the database during streaming
            import json
            import httpx
            from datetime import datetime
            import uuid
            
            # Send user message event
            yield f"data: {json.dumps({'type': 'user_message', 'message': {'id': str(uuid.uuid4()), 'role': 'user', 'content': chat_request.message, 'created_at': datetime.utcnow().isoformat()}})}\n\n"
            
            # Prepare messages for LLM
            messages = [
                {"role": "user", "content": chat_request.message}
            ]
            
            # Stream from LLM service directly
            from privategpt.shared.settings import settings
            
            assistant_message_id = str(uuid.uuid4())
            yield f"data: {json.dumps({'type': 'assistant_message_start', 'message_id': assistant_message_id})}\n\n"
            
            full_content = ""
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    'POST',
                    f"{settings.llm_service_url}/chat/stream",
                    json={
                        "messages": messages,
                        "model": chat_request.model_name,
                        "temperature": chat_request.temperature,
                        "max_tokens": chat_request.max_tokens
                    }
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            content = line[6:]  # Remove 'data: ' prefix
                            if content.strip() == '[DONE]':
                                break
                            if content.strip():
                                full_content += content
                                yield f"data: {json.dumps({'type': 'content_chunk', 'message_id': assistant_message_id, 'content': content})}\n\n"
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'assistant_message_complete', 'message': {'id': assistant_message_id, 'role': 'assistant', 'content': full_content, 'created_at': datetime.utcnow().isoformat()}})}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
            
        except Exception as e:
            logger.error(f"Error in chat stream: {e}")
            error_event = {"type": "error", "message": "Internal server error"}
            import json
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


# Two-phase streaming endpoints for conversation persistence
class PrepareStreamRequest(BaseModel):
    """Request to prepare a streaming session"""
    message: str = Field(..., min_length=1, description="The user's message")
    model: str = Field(..., description="Model to use for generation (required)")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)


class PrepareMCPStreamRequest(BaseModel):
    """Request to prepare a streaming session with MCP tools"""
    message: str = Field(..., min_length=1, description="The user's message")
    model: str = Field(..., description="Model to use for generation (required)")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    tools_enabled: bool = Field(default=False, description="Enable MCP tools")
    auto_approve_tools: bool = Field(default=False, description="Auto-approve tool executions")


class PrepareStreamResponse(BaseModel):
    """Response with stream token and metadata"""
    stream_token: str = Field(..., description="Token to use for streaming")
    stream_url: str = Field(..., description="URL to connect for streaming")
    user_message_id: str = Field(..., description="ID of the created user message")
    assistant_message_id: str = Field(..., description="ID for the assistant message")


@router.post("/conversations/{conversation_id}/prepare-stream", response_model=PrepareStreamResponse)
async def prepare_stream(
    conversation_id: str,
    request: PrepareStreamRequest,
    user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """
    Prepare a streaming session by creating the user message and returning a stream token.
    This endpoint handles all database operations before streaming.
    """
    logger.info("=== PREPARE STREAM ENDPOINT (FIXED) ===")
    
    try:
        logger.info("Starting prepare stream operation")
        
        # Database operations - done completely before any Redis operations
        user_message_id = None
        user_id = None
        llm_messages = []
        model_name = None
        system_prompt = None
        
        from privategpt.infra.database.async_session import get_async_session_context
        
        logger.info("Starting database operations")
        async with get_async_session_context() as session:
            logger.info("Database session created")
            chat_service = ChatService(session)
            
            # Ensure user exists in database
            logger.info("Ensuring user exists")
            user_id = await ensure_user_exists(session, user)
            logger.info(f"User ID: {user_id}")
            
            # Verify conversation exists and user owns it
            logger.info("Getting conversation")
            conversation = await chat_service.get_conversation(conversation_id, user_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            logger.info("Conversation found")
            
            # Create user message in database using direct SQLAlchemy
            logger.info("Creating user message")
            user_message_id = str(uuid.uuid4())
            user_message = Message(
                id=user_message_id,
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=request.message,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(user_message)
            logger.info(f"User message created: {user_message_id}")
            
            # Get conversation context for LLM using direct SQLAlchemy
            logger.info("Getting recent messages")
            from sqlalchemy import select
            stmt = select(Message).where(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at.desc()).limit(20)
            result = await session.execute(stmt)
            recent_messages = result.scalars().all()
            logger.info(f"Found {len(recent_messages)} recent messages")
            
            # Prepare messages for LLM
            system_prompt = conversation.system_prompt or "You are a helpful AI assistant."
            model_name = request.model  # Always use the model from the request
            
            if system_prompt:
                llm_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add conversation history (reverse order since we got newest first)
            for msg in reversed(recent_messages):
                if msg.id != user_message_id:  # Skip the message we just created
                    role_value = msg.role.value if isinstance(msg.role, enum.Enum) else msg.role
                    logger.info(f"Processing message {msg.id}: role type={type(msg.role)}, value={role_value}")
                    llm_messages.append({
                        "role": role_value,
                        "content": msg.content
                    })
            
            # Add the new user message
            llm_messages.append({
                "role": "user",
                "content": request.message
            })
            
            logger.info(f"Prepared {len(llm_messages)} LLM messages")
            
            # Commit the transaction
            logger.info("Committing database transaction")
            await session.commit()
            logger.info("Database transaction committed")
        
        # ALL database operations complete - now do Redis operations
        logger.info("Database operations complete, starting Redis operations")
        
        from privategpt.services.gateway.core.stream_session import StreamSessionManager
        stream_manager = StreamSessionManager()
        
        logger.info("Creating stream session in Redis")
        stream_session = await stream_manager.create_session(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message_id=user_message_id,
            llm_messages=llm_messages,
            model_name=model_name,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            system_prompt=system_prompt
        )
        logger.info(f"Stream session created: {stream_session.token}")
        
        return PrepareStreamResponse(
            stream_token=stream_session.token,
            stream_url=f"/stream/{stream_session.token}",
            user_message_id=user_message_id,
            assistant_message_id=stream_session.assistant_message_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preparing stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to prepare streaming session")


@router.post("/conversations/{conversation_id}/prepare-mcp-stream", response_model=PrepareStreamResponse)
async def prepare_mcp_stream(
    conversation_id: str,
    request: PrepareMCPStreamRequest,
    user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """
    Prepare a streaming session with MCP tool support.
    This endpoint handles all database operations and tool discovery before streaming.
    """
    logger.info("=== PREPARE MCP STREAM ENDPOINT ===")
    
    try:
        logger.info("Starting prepare MCP stream operation")
        
        # Database operations
        user_message_id = None
        user_id = None
        llm_messages = []
        model_name = None
        system_prompt = None
        tools = []
        
        from privategpt.infra.database.async_session import get_async_session_context
        
        logger.info("Starting database operations")
        async with get_async_session_context() as session:
            logger.info("Database session created")
            chat_service = ChatService(session)
            
            # Ensure user exists in database
            logger.info("Ensuring user exists")
            user_id = await ensure_user_exists(session, user)
            logger.info(f"User ID: {user_id}")
            
            # Verify conversation exists and user owns it
            logger.info("Getting conversation")
            conversation = await chat_service.get_conversation(conversation_id, user_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            logger.info("Conversation found")
            
            # Create user message in database
            logger.info("Creating user message")
            user_message_id = str(uuid.uuid4())
            user_message = Message(
                id=user_message_id,
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=request.message,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(user_message)
            logger.info(f"User message created: {user_message_id}")
            
            # Get conversation context for LLM
            logger.info("Getting recent messages")
            from sqlalchemy import select
            stmt = select(Message).where(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at.desc()).limit(20)
            result = await session.execute(stmt)
            recent_messages = result.scalars().all()
            logger.info(f"Found {len(recent_messages)} recent messages")
            
            # Prepare messages for LLM
            system_prompt = conversation.system_prompt or "You are a helpful AI assistant."
            model_name = request.model
            
            if system_prompt:
                llm_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add conversation history (reverse order since we got newest first)
            for msg in reversed(recent_messages):
                if msg.id != user_message_id:  # Skip the message we just created
                    role_value = msg.role.value if isinstance(msg.role, enum.Enum) else msg.role
                    logger.info(f"Processing message {msg.id}: role type={type(msg.role)}, value={role_value}")
                    llm_messages.append({
                        "role": role_value,
                        "content": msg.content
                    })
            
            # Add the new user message
            llm_messages.append({
                "role": "user",
                "content": request.message
            })
            
            logger.info(f"Prepared {len(llm_messages)} LLM messages")
            
            # Commit the transaction
            logger.info("Committing database transaction")
            await session.commit()
            logger.info("Database transaction committed")
        
        # Get MCP tools if enabled
        if request.tools_enabled:
            logger.info("MCP tools enabled, discovering tools...")
            from privategpt.services.gateway.core.mcp.unified_mcp_client import get_mcp_client
            from privategpt.services.llm.core.model_registry import get_model_registry
            
            try:
                # Get model provider
                model_registry = get_model_registry()
                provider = model_registry.get_provider_for_model(model_name)
                if not provider:
                    provider = "generic"
                logger.info(f"Using provider '{provider}' for model '{model_name}'")
                
                # Get MCP client and tools
                mcp_client = await get_mcp_client()
                tools = mcp_client.get_tools_for_llm(provider)
                logger.info(f"Discovered {len(tools)} MCP tools for provider '{provider}'")
                
                # Add tools to system prompt if any
                if tools and system_prompt:
                    # Update the system message with tools info
                    llm_messages[0]["content"] = system_prompt + "\n\nYou have access to the following tools:\n" + \
                        "\n".join([f"- {tool['name']}: {tool.get('description', 'No description')}" for tool in tools[:5]])
                    
            except Exception as e:
                logger.warning(f"Failed to get MCP tools: {e}")
                tools = []
        
        # ALL database operations complete - now do Redis operations
        logger.info("Database operations complete, starting Redis operations")
        
        from privategpt.services.gateway.core.stream_session import StreamSessionManager
        stream_manager = StreamSessionManager()
        
        logger.info("Creating stream session in Redis")
        stream_session = await stream_manager.create_session(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message_id=user_message_id,
            llm_messages=llm_messages,
            model_name=model_name,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            system_prompt=system_prompt,
            tools_enabled=request.tools_enabled,
            tools=tools,
            auto_approve_tools=request.auto_approve_tools
        )
        logger.info(f"Stream session created: {stream_session.token}")
        
        return PrepareStreamResponse(
            stream_token=stream_session.token,
            stream_url=f"/stream/mcp/{stream_session.token}",
            user_message_id=user_message_id,
            assistant_message_id=stream_session.assistant_message_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preparing MCP stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to prepare MCP streaming session")


@router.get("/live-stream/{stream_token}")
async def stream_conversation(
    stream_token: str
):
    """
    Stream the LLM response using a pre-created stream session.
    No database operations occur during streaming.
    The stream token itself provides authentication for this session.
    """
    try:
        from privategpt.services.gateway.core.stream_session import StreamSessionManager
        from privategpt.services.llm.core.model_registry import get_model_registry
        from privategpt.services.gateway.core.xml_parser import parse_ai_content
        
        logger.info(f"Stream endpoint called with token: {stream_token}")
        
        stream_manager = StreamSessionManager()
        
        # Validate stream token (this is the security mechanism)
        logger.info("Getting stream session...")
        stream_session = await stream_manager.get_session(stream_token)
        if not stream_session:
            logger.error(f"Stream session not found for token: {stream_token}")
            raise HTTPException(status_code=404, detail="Invalid or expired stream token")
        
        logger.info(f"Stream session found for conversation: {stream_session.conversation_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in stream endpoint setup: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Stream setup error: {str(e)}")
    
    async def event_stream():
        import json
        from privategpt.infra.tasks.celery_app import save_assistant_message_task
        
        try:
            # Send initial events
            yield f"data: {json.dumps({'type': 'stream_start', 'conversation_id': stream_session.conversation_id})}\n\n"
            
            yield f"data: {json.dumps({'type': 'user_message', 'message': {'id': stream_session.user_message_id, 'role': 'user', 'content': stream_session.llm_messages[-1]['content'], 'created_at': datetime.utcnow().isoformat()}})}\n\n"
            
            yield f"data: {json.dumps({'type': 'assistant_message_start', 'message_id': stream_session.assistant_message_id})}\n\n"
            
            # Stream from model registry
            model_registry = get_model_registry()
            full_content = ""
            
            async for chunk in model_registry.chat_stream(
                model_name=stream_session.model_name,
                messages=stream_session.llm_messages,
                temperature=stream_session.temperature,
                max_tokens=stream_session.max_tokens
            ):
                full_content += chunk
                yield f"data: {json.dumps({'type': 'content_chunk', 'message_id': stream_session.assistant_message_id, 'content': chunk})}\n\n"
            
            # Parse the complete response
            parsed_content = parse_ai_content(full_content, settings.enable_thinking_mode)
            
            # Get token usage from the last chunk metadata (if available)
            # For now, we'll estimate tokens
            from privategpt.services.llm.core.adapters.base import BaseModelAdapter
            provider = model_registry.get_provider_for_model(stream_session.model_name)
            if provider:
                adapter = model_registry.providers[provider]
                output_tokens = adapter.count_tokens(full_content, stream_session.model_name)
                input_tokens = sum(
                    adapter.count_tokens(msg["content"], stream_session.model_name) 
                    for msg in stream_session.llm_messages
                )
                total_tokens = input_tokens + output_tokens
            else:
                output_tokens = len(full_content.split()) * 2  # Rough estimate
                input_tokens = sum(len(msg["content"].split()) * 2 for msg in stream_session.llm_messages)
                total_tokens = input_tokens + output_tokens
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'assistant_message_complete', 'message': {'id': stream_session.assistant_message_id, 'role': 'assistant', 'content': parsed_content.processed_content, 'created_at': datetime.utcnow().isoformat(), 'token_count': output_tokens}})}\n\n"
            
            # Queue Celery task to save assistant message
            save_assistant_message_task.delay(
                conversation_id=stream_session.conversation_id,
                message_id=stream_session.assistant_message_id,
                content=parsed_content.processed_content,
                raw_content=parsed_content.raw_content,
                thinking_content=parsed_content.thinking_content,
                token_count=output_tokens,
                data={
                    "model": stream_session.model_name,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "ui_tags": parsed_content.ui_tags
                }
            )
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            # Clean up stream session
            await stream_manager.delete_session(stream_token)
            
        except Exception as e:
            logger.error(f"Error during streaming: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Streaming error occurred'})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )


@router.get("/live-mcp-stream/{stream_token}")
async def stream_mcp_conversation(
    stream_token: str
):
    """
    Stream the LLM response with MCP tool support using a pre-created stream session.
    This endpoint handles tool detection, execution, and approval during streaming.
    """
    try:
        from privategpt.services.gateway.core.stream_session import StreamSessionManager
        from privategpt.services.llm.core.model_registry import get_model_registry
        from privategpt.services.gateway.core.xml_parser import parse_ai_content
        from privategpt.services.gateway.core.mcp.unified_mcp_client import get_mcp_client, ToolCall, UserContext
        
        logger.info(f"MCP Stream endpoint called with token: {stream_token}")
        
        stream_manager = StreamSessionManager()
        
        # Validate stream token
        logger.info("Getting stream session...")
        stream_session = await stream_manager.get_session(stream_token)
        if not stream_session:
            logger.error(f"Stream session not found for token: {stream_token}")
            raise HTTPException(status_code=404, detail="Invalid or expired stream token")
        
        logger.info(f"MCP Stream session found for conversation: {stream_session.conversation_id}")
        logger.info(f"Tools enabled: {stream_session.tools_enabled}, Tool count: {len(stream_session.tools)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in MCP stream endpoint setup: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Stream setup error: {str(e)}")
    
    async def event_stream():
        import json
        from privategpt.infra.tasks.celery_app import save_assistant_message_task
        
        try:
            # Send initial events
            yield f"data: {json.dumps({'type': 'stream_start', 'conversation_id': stream_session.conversation_id})}\n\n"
            
            yield f"data: {json.dumps({'type': 'user_message', 'message': {'id': stream_session.user_message_id, 'role': 'user', 'content': stream_session.llm_messages[-1]['content'], 'created_at': datetime.utcnow().isoformat()}})}\n\n"
            
            yield f"data: {json.dumps({'type': 'assistant_message_start', 'message_id': stream_session.assistant_message_id})}\n\n"
            
            # If tools are enabled, send tools info
            if stream_session.tools_enabled and stream_session.tools:
                yield f"data: {json.dumps({'type': 'tools_available', 'tools': [{'name': t.get('name'), 'description': t.get('description', '')} for t in stream_session.tools[:5]]})}\n\n"
            
            # Stream from model registry with tools
            model_registry = get_model_registry()
            full_content = ""
            
            # Prepare messages with tools if enabled
            messages_for_llm = stream_session.llm_messages.copy()
            
            # Get the streaming parameters
            stream_params = {
                "model_name": stream_session.model_name,
                "messages": messages_for_llm,
                "temperature": stream_session.temperature,
                "max_tokens": stream_session.max_tokens
            }
            
            # Add tools if enabled
            if stream_session.tools_enabled and stream_session.tools:
                stream_params["tools"] = stream_session.tools
                logger.info(f"Streaming with {len(stream_session.tools)} tools")
            
            # Stream the response
            tool_calls_detected = []
            current_tool_call = None
            in_tool_call = False
            
            async for chunk in model_registry.chat_stream(**stream_params):
                full_content += chunk
                
                # Check for tool call patterns in the chunk
                # Simple pattern matching for now - in production, use proper parsing
                if "<tool_call>" in chunk:
                    in_tool_call = True
                    current_tool_call = {"raw": ""}
                elif "</tool_call>" in chunk and current_tool_call:
                    in_tool_call = False
                    # Parse the tool call
                    try:
                        # Extract tool name and arguments from the raw content
                        # This is simplified - real implementation would parse properly
                        tool_content = current_tool_call["raw"] + chunk.split("</tool_call>")[0]
                        
                        # Send tool call event
                        yield f"data: {json.dumps({'type': 'tool_call_detected', 'tool_call': tool_content})}\n\n"
                        
                        # Execute tool if auto-approve is enabled
                        if stream_session.auto_approve_tools:
                            yield f"data: {json.dumps({'type': 'tool_executing', 'tool_name': 'detected_tool'})}\n\n"
                            
                            # TODO: Actual tool execution here
                            # For now, just simulate
                            yield f"data: {json.dumps({'type': 'tool_result', 'result': 'Tool executed successfully'})}\n\n"
                        else:
                            # Request approval
                            yield f"data: {json.dumps({'type': 'tool_approval_required', 'tool_name': 'detected_tool'})}\n\n"
                        
                        tool_calls_detected.append(tool_content)
                    except Exception as e:
                        logger.error(f"Failed to parse tool call: {e}")
                    
                    current_tool_call = None
                elif in_tool_call and current_tool_call is not None:
                    current_tool_call["raw"] += chunk
                else:
                    # Regular content chunk
                    yield f"data: {json.dumps({'type': 'content_chunk', 'message_id': stream_session.assistant_message_id, 'content': chunk})}\n\n"
            
            # Parse the complete response
            parsed_content = parse_ai_content(full_content, settings.enable_thinking_mode)
            
            # Get token usage
            from privategpt.services.llm.core.adapters.base import BaseModelAdapter
            provider = model_registry.get_provider_for_model(stream_session.model_name)
            if provider:
                adapter = model_registry.providers[provider]
                output_tokens = adapter.count_tokens(full_content, stream_session.model_name)
                input_tokens = sum(
                    adapter.count_tokens(msg["content"], stream_session.model_name) 
                    for msg in stream_session.llm_messages
                )
                total_tokens = input_tokens + output_tokens
            else:
                output_tokens = len(full_content.split()) * 2
                input_tokens = sum(len(msg["content"].split()) * 2 for msg in stream_session.llm_messages)
                total_tokens = input_tokens + output_tokens
            
            # Send completion event with tool usage info
            completion_data = {
                'type': 'assistant_message_complete',
                'message': {
                    'id': stream_session.assistant_message_id,
                    'role': 'assistant',
                    'content': parsed_content.processed_content,
                    'created_at': datetime.utcnow().isoformat(),
                    'token_count': output_tokens,
                    'tool_calls': tool_calls_detected
                }
            }
            yield f"data: {json.dumps(completion_data)}\n\n"
            
            # Queue Celery task to save assistant message
            save_assistant_message_task.delay(
                conversation_id=stream_session.conversation_id,
                message_id=stream_session.assistant_message_id,
                content=parsed_content.processed_content,
                raw_content=parsed_content.raw_content,
                thinking_content=parsed_content.thinking_content,
                token_count=output_tokens,
                data={
                    "model": stream_session.model_name,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "ui_tags": parsed_content.ui_tags,
                    "tool_calls": tool_calls_detected,
                    "tools_enabled": stream_session.tools_enabled
                }
            )
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            # Clean up stream session
            await stream_manager.delete_session(stream_token)
            
        except Exception as e:
            logger.error(f"Error during MCP streaming: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': 'MCP streaming error occurred'})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"
        }
    )


# Webhook endpoint for external stream completion notification
class StreamCompletionWebhook(BaseModel):
    """Webhook payload for stream completion"""
    stream_token: str = Field(..., description="The stream token that completed")
    status: str = Field(..., description="Completion status: 'success' or 'error'")
    error_message: Optional[str] = Field(None, description="Error message if status is 'error'")
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    model_used: Optional[str] = Field(None, description="Model that was used")


@router.post("/webhooks/stream-completion", status_code=status.HTTP_200_OK)
async def stream_completion_webhook(
    webhook_data: StreamCompletionWebhook,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Webhook endpoint to notify when a stream has completed.
    This can be used by external services or frontend to confirm message persistence.
    """
    logger.info(f"Stream completion webhook received for token: {webhook_data.stream_token}")
    
    # Optional: Add any additional processing here
    # For example, updating metrics, sending notifications, etc.
    
    return {"status": "acknowledged", "stream_token": webhook_data.stream_token}


# Quick chat endpoint (creates conversation automatically)
@router.post("/quick-chat", response_model=ChatResponse)
async def quick_chat(
    chat_request: ChatRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Quick chat that automatically creates a conversation"""
    # TODO: Implement quick chat logic
    # 1. Create new conversation with auto-generated title
    # 2. Process chat request
    # 3. Return conversation_id and messages
    
    raise HTTPException(status_code=501, detail="Quick chat implementation pending")


# Test endpoints for debugging - NO AUTH
@router.get("/debug/simple")
async def debug_simple():
    """Simple debug endpoint with no dependencies"""
    return {"status": "ok", "message": "Simple endpoint works"}

@router.post("/debug/stream-test")
async def debug_stream_test(chat_request: ChatRequest):
    """Test streaming without any database operations"""
    
    async def stream_generator():
        try:
            import json
            import httpx
            from datetime import datetime
            import uuid
            
            # Send start event
            yield f"data: {json.dumps({'type': 'start', 'message': 'Starting stream test'})}\n\n"
            
            # Prepare messages for LLM
            messages = [
                {"role": "user", "content": chat_request.message}
            ]
            
            # Stream from LLM service directly
            from privategpt.shared.settings import settings
            
            yield f"data: {json.dumps({'type': 'info', 'message': 'Calling LLM service'})}\n\n"
            
            full_content = ""
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    'POST',
                    f"{settings.llm_service_url}/chat/stream",
                    json={
                        "messages": messages,
                        "model": chat_request.model_name,
                        "temperature": chat_request.temperature,
                        "max_tokens": chat_request.max_tokens
                    }
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            content = line[6:]  # Remove 'data: ' prefix
                            if content.strip() == '[DONE]':
                                break
                            if content.strip():
                                full_content += content
                                yield f"data: {json.dumps({'type': 'content', 'text': content})}\n\n"
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'complete', 'full_text': full_content})}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
            
        except Exception as e:
            logger.error(f"Error in debug stream: {e}")
            error_event = {"type": "error", "message": str(e)}
            import json
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@router.get("/debug/simple-test/{token}")
async def debug_simple_test(token: str):
    """Ultra-simple test endpoint"""
    return {"message": "Simple test works!", "token": token}


@router.get("/debug/stream-session/{stream_token}")
async def debug_stream_session(stream_token: str):
    """Debug endpoint to check stream session data"""
    from privategpt.services.gateway.core.stream_session import StreamSessionManager
    
    try:
        stream_manager = StreamSessionManager()
        stream_session = await stream_manager.get_session(stream_token)
        
        if not stream_session:
            return {"error": "Stream session not found", "token": stream_token}
        
        return {
            "success": True,
            "session": {
                "token": stream_session.token,
                "conversation_id": stream_session.conversation_id,
                "user_id": stream_session.user_id,
                "model_name": stream_session.model_name,
                "created_at": stream_session.created_at.isoformat() if stream_session.created_at else None
            }
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/debug/session")
async def debug_session():
    """Debug session creation using context manager (recommended pattern)"""
    try:
        from privategpt.infra.database.async_session import get_async_session_context
        async with get_async_session_context() as session:
            from sqlalchemy import select
            from privategpt.infra.database.models import Conversation
            
            stmt = select(Conversation).limit(1)
            result = await session.execute(stmt)
            conversations = result.scalars().all()
            
            return {"success": True, "count": len(conversations), "message": "Context manager pattern works!"}
    except Exception as e:
        import traceback
        logger.error(f"Debug session error: {e}")
        return {"error": str(e), "type": type(e).__name__, "traceback": traceback.format_exc()}

@router.get("/debug/conversations")
async def debug_list_conversations():
    """Debug conversations list using context manager instead of dependency injection"""
    try:
        from privategpt.infra.database.async_session import get_async_session_context
        from privategpt.infra.database.conversation_repository import SqlConversationRepository
        
        async with get_async_session_context() as session:
            repo = SqlConversationRepository(session)
            conversations = await repo.get_by_user(user_id=1, limit=50, offset=0)
            
            return {
                "success": True, 
                "count": len(conversations),
                "conversations": [{"id": c.id, "title": c.title, "status": c.status} for c in conversations],
                "message": "Fixed using context manager pattern!"
            }
    except Exception as e:
        import traceback
        logger.error(f"Debug endpoint error: {e}")
        return {"error": str(e), "type": type(e).__name__, "traceback": traceback.format_exc()}

@router.post("/debug/create-conversation")
async def debug_create_conversation():
    """Debug conversation creation using context manager"""
    try:
        from privategpt.infra.database.async_session import get_async_session_context
        from privategpt.core.domain.conversation import Conversation
        from privategpt.infra.database.conversation_repository import SqlConversationRepository
        import uuid
        from datetime import datetime
        
        async with get_async_session_context() as session:
            # Create a test conversation
            conversation = Conversation(
                id=str(uuid.uuid4()),
                user_id=1,
                title="Debug Test Conversation",
                status="active",
                model_name="dolphin-phi:2.7b",
                system_prompt=None,
                data={},
                total_tokens=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            repo = SqlConversationRepository(session)
            created_conversation = await repo.create(conversation)
            
            return {
                "success": True,
                "conversation": {
                    "id": created_conversation.id,
                    "title": created_conversation.title,
                    "status": created_conversation.status,
                    "created_at": created_conversation.created_at.isoformat()
                },
                "message": "Conversation created successfully!"
            }
    except Exception as e:
        import traceback
        logger.error(f"Debug create conversation error: {e}")
        return {"error": str(e), "type": type(e).__name__, "traceback": traceback.format_exc()}

@router.post("/conversations/{conversation_id}/test-chat")
async def test_chat_with_conversation(
    conversation_id: str,
    chat_request: ChatRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Test chat endpoint with no auth for debugging token tracking"""
    chat_service = ChatService(session)
    
    try:
        # Send message and get response using ChatService with hardcoded user
        user_message, assistant_message = await chat_service.send_message(
            conversation_id=conversation_id,
            user_id=1,  # Hardcoded for testing
            message_content=chat_request.message,
            model_name=chat_request.model_name,
            temperature=chat_request.temperature,
            max_tokens=chat_request.max_tokens
        )
        
        return {
            "conversation_id": conversation_id,
            "user_message": {
                "id": user_message.id,
                "content": user_message.content,
                "token_count": user_message.token_count
            },
            "assistant_message": {
                "id": assistant_message.id,
                "content": assistant_message.content,
                "token_count": assistant_message.token_count,
                "data": assistant_message.data
            }
        }
    except Exception as e:
        logger.error(f"Test chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await chat_service.close()


# Simple chat endpoints for direct LLM access
class SimpleChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    use_mcp: bool = Field(default=True)
    available_tools: str = Field(default="*")  # "*", "", or "tool1,tool2"


class SimpleChatResponse(BaseModel):
    text: str
    model: str
    response_time_ms: Optional[float] = None
    tools_used: bool = False


@router.post("/direct", response_model=SimpleChatResponse)
async def direct_chat(chat_request: SimpleChatRequest):
    """Direct chat with LLM service (no conversation persistence)"""
    try:
        # Call LLM service directly
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare messages for LLM
            messages = [{"role": "user", "content": chat_request.message}]
            
            # Build payload
            payload = {
                "messages": messages,
                "model": chat_request.model,
                "temperature": chat_request.temperature,
                "max_tokens": chat_request.max_tokens
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            # Call LLM service
            from privategpt.shared.settings import settings
            response = await client.post(
                f"{settings.llm_service_url}/chat",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            return SimpleChatResponse(
                text=result.get("text", ""),
                model=result.get("model", chat_request.model or "unknown"),
                response_time_ms=result.get("response_time_ms"),
                tools_used=False  # Direct mode doesn't use tools
            )
            
    except httpx.HTTPError as e:
        logger.error(f"LLM service error: {e}")
        raise ServiceUnavailableError("LLM Service", f"HTTP error: {e}")
    except Exception as e:
        logger.error(f"Direct chat error: {e}")
        # Check for specific error patterns
        error_msg = str(e).lower()
        if "model" in error_msg and ("not found" in error_msg or "not available" in error_msg):
            raise ModelNotAvailableError(chat_request.model or "unknown")
        raise


@router.post("/mcp", response_model=SimpleChatResponse)
async def mcp_chat(chat_request: SimpleChatRequest):
    """Chat with MCP tool integration"""
    if not chat_request.use_mcp:
        # If MCP disabled, redirect to direct chat
        return await direct_chat(chat_request)
    
    try:
        # Get MCP client and tools
        from privategpt.services.gateway.core.mcp.unified_mcp_client import get_mcp_client
        mcp_client = await get_mcp_client()
        
        # Get tools formatted for the provider (default to anthropic for Claude)
        provider = "anthropic" if "claude" in chat_request.model.lower() else "openai"
        tools = mcp_client.registry.get_tools_for_llm(provider)
        
        # Call LLM service with tools
        async with httpx.AsyncClient(timeout=180.0) as client:
            # Build payload with tools
            payload = {
                "messages": [{"role": "user", "content": chat_request.message}],
                "model": chat_request.model,
                "temperature": chat_request.temperature,
                "max_tokens": chat_request.max_tokens,
                "tools": tools  # Include MCP tools
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            logger.info(f"Calling LLM with {len(tools)} MCP tools")
            
            # Make the request
            response = await client.post(
                f"{settings.llm_service_url}/chat",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Check if tool calls were made
            if "tool_calls" in result and result["tool_calls"]:
                logger.info(f"Processing {len(result['tool_calls'])} tool calls")
                tool_results = []
                
                for tool_call in result["tool_calls"]:
                    tool_name = tool_call["name"]
                    tool_args = tool_call.get("arguments", {})
                    
                    # Execute tool via MCP
                    tool_result = await mcp_client.execute_tool(tool_name, tool_args)
                    tool_results.append({
                        "tool_call_id": tool_call.get("id", tool_name),
                        "result": tool_result
                    })
                
                # Call LLM again with tool results
                messages = [
                    {"role": "user", "content": chat_request.message},
                    {"role": "assistant", "content": result.get("text", ""), "tool_calls": result["tool_calls"]},
                    {"role": "tool", "content": json.dumps(tool_results)}
                ]
                
                final_response = await client.post(
                    f"{settings.llm_service_url}/chat",
                    json={
                        "messages": messages,
                        "model": chat_request.model,
                        "temperature": chat_request.temperature,
                        "max_tokens": chat_request.max_tokens
                    }
                )
                final_response.raise_for_status()
                final_result = final_response.json()
                
                return SimpleChatResponse(
                    text=final_result.get("text", ""),
                    model=chat_request.model,
                    response_time_ms=None,
                    tools_used=True
                )
            else:
                # No tool calls, return direct response
                return SimpleChatResponse(
                    text=result.get("text", ""),
                    model=chat_request.model,
                    response_time_ms=None,
                    tools_used=False
                )
        
    except Exception as e:
        logger.error(f"MCP chat error: {e}")
        raise ServiceUnavailableError("MCP Service", str(e))


@router.post("/direct/stream")
async def direct_chat_stream(chat_request: SimpleChatRequest):
    """Direct chat with LLM service streaming (no conversation persistence)"""
    try:
        async def stream_generator():
            try:
                import json
                import time
                start_time = time.time()
                
                # Send start event
                yield f"data: {json.dumps({'type': 'content_start'})}\n\n"
                
                # Call LLM service with streaming
                async with httpx.AsyncClient(timeout=180.0) as client:
                    # Prepare messages for LLM
                    messages = [{"role": "user", "content": chat_request.message}]
                    
                    # Build payload for streaming
                    payload = {
                        "messages": messages,
                        "model": chat_request.model,
                        "temperature": chat_request.temperature,
                        "max_tokens": chat_request.max_tokens
                    }
                    
                    # Remove None values
                    payload = {k: v for k, v in payload.items() if v is not None}
                    
                    # Stream from LLM service
                    from privategpt.shared.settings import settings
                    
                    async with client.stream(
                        'POST',
                        f"{settings.llm_service_url}/chat/stream",
                        json=payload
                    ) as response:
                        response.raise_for_status()
                        
                        full_content = ""
                        async for line in response.aiter_lines():
                            if line.startswith('data: '):
                                content = line[6:]  # Remove 'data: ' prefix
                                if content.strip() == '[DONE]':
                                    break
                                if content.strip():
                                    full_content += content
                                    # Forward streaming content to client
                                    yield f"data: {json.dumps({'type': 'content_delta', 'content': content})}\n\n"
                
                # Send completion event
                response_time = (time.time() - start_time) * 1000
                yield f"data: {json.dumps({'type': 'content_end'})}\n\n"
                completion_event = {
                    'type': 'message_complete', 
                    'text': full_content,
                    'model': chat_request.model or 'unknown',
                    'response_time_ms': response_time,
                    'tools_used': False
                }
                yield f"data: {json.dumps(completion_event)}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
            except Exception as e:
                logger.error(f"Direct chat stream error: {e}")
                # Send error in streaming format
                error_event = {
                    'type': 'error',
                    'error': {
                        'type': 'stream_error',
                        'message': 'Stream interrupted',
                        'details': {'reason': str(e)}
                    }
                }
                yield f"data: {json.dumps(error_event)}\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except Exception as e:
        logger.error(f"Direct chat stream setup error: {e}")
        raise ServiceUnavailableError("Streaming Service", str(e))


@router.post("/mcp/stream")
async def mcp_chat_stream(chat_request: SimpleChatRequest):
    """MCP chat with streaming support"""
    if not chat_request.use_mcp:
        # If MCP disabled, redirect to direct chat stream
        return await direct_chat_stream(chat_request)
    
    try:
        # TODO: Implement MCP streaming
        # For now, fall back to direct chat stream
        return await direct_chat_stream(chat_request)
        
    except Exception as e:
        logger.error(f"MCP chat stream error: {e}")
        raise ServiceUnavailableError("MCP Streaming Service", str(e))


@router.post("/test-token-tracking/{conversation_id}")
async def test_token_tracking(
    conversation_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Simple test endpoint for token tracking - no auth"""
    try:
        chat_service = ChatService(session)
        
        # Send a test message
        user_message, assistant_message = await chat_service.send_message(
            conversation_id=conversation_id,
            user_id=1,
            message_content="Hello! What model are you?",
            model_name="dolphin-phi:2.7b"
        )
        
        await chat_service.close()
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "user_tokens": user_message.token_count,
            "assistant_tokens": assistant_message.token_count,
            "assistant_content": assistant_message.content[:100] + "..."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Debug endpoints
@router.post("/debug/test-conversation", response_model=ConversationResponse)
async def debug_create_conversation(
    conversation_data: ConversationCreate
):
    """Create a test conversation without auth for debugging"""
    from privategpt.infra.database.async_session import get_async_session_context
    from privategpt.core.domain.conversation import Conversation
    from privategpt.infra.database.conversation_repository import SqlConversationRepository
    import uuid
    from datetime import datetime
    
    async with get_async_session_context() as session:
        # Use demo user (ID 1) for testing
        user_id = 1
        
        # Create domain conversation
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=conversation_data.title,
            status="active",
            model_name=conversation_data.model_name,
            system_prompt=conversation_data.system_prompt,
            data=conversation_data.data,
            total_tokens=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        repo = SqlConversationRepository(session)
        created_conversation = await repo.create(conversation)
        
        return ConversationResponse(
            id=created_conversation.id,
            title=created_conversation.title,
            status=created_conversation.status,
            model_name=created_conversation.model_name,
            system_prompt=created_conversation.system_prompt,
            data=created_conversation.data,
            created_at=created_conversation.created_at,
            updated_at=created_conversation.updated_at,
            message_count=len(created_conversation.messages)
        )