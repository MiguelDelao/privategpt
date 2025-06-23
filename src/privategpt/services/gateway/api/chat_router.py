from __future__ import annotations

"""
Chat and conversation management API routes for the gateway.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.shared.auth_middleware import get_current_user
from fastapi import Depends
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

logger = logging.getLogger(__name__)


# Authentication helper functions removed - using proper auth dependencies now


async def ensure_user_exists(session: AsyncSession, user_claims: Dict[str, Any]) -> int:
    """Ensure user exists in database, create if not found"""
    # Handle case when auth is disabled (for debugging)
    if not user_claims or user_claims.get("user_id") is None:
        logger.warning("Auth disabled or invalid user claims, using demo user")
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
    
    keycloak_user_id = user_claims.get("user_id")  # This is the Keycloak UUID from 'sub'
    logger.info(f"Looking up user with keycloak_id: {keycloak_user_id}")
    
    # Check if user exists by keycloak_id
    stmt = select(User).where(User.keycloak_id == keycloak_user_id)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        logger.info(f"Found existing user: {existing_user.id} ({existing_user.email})")
        return existing_user.id
    
    # Create new user (let database auto-assign integer ID)
    try:
        new_user = User(
            keycloak_id=keycloak_user_id,
            email=user_claims.get("email"),
            username=user_claims.get("preferred_username"),
            first_name=user_claims.get("given_name"),
            last_name=user_claims.get("family_name"),
            role="user",
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
    model_name: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    use_mcp: bool = Field(default=True)
    available_tools: str = Field(default="*")  # "*", "", or "tool1,tool2"


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
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a conversation"""
    chat_service = ChatService(session)
    
    try:
        # Ensure user exists in database (auto-create if needed)
        user_id = await ensure_user_exists(session, user)
        
        # Verify conversation exists and user owns it
        conversation = await chat_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Soft delete by updating status
        success = await chat_service.conversation_repo.delete(conversation_id)
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
                role=msg.role,
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
        from privategpt.core.domain.message import Message as DomainMessage
        
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
            role=created_message.role,
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
                role=user_message.role,
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
                role=assistant_message.role,
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
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Stream chat response for a conversation"""
    
    async def stream_generator():
        chat_service = ChatService(session)
        
        try:
            # Ensure user exists in database (auto-create if needed)
            user_id = await ensure_user_exists(session, user)
            
            async for event in chat_service.stream_message(
                conversation_id=conversation_id,
                user_id=user_id,
                message_content=chat_request.message,
                model_name=chat_request.model_name,
                temperature=chat_request.temperature,
                max_tokens=chat_request.max_tokens
            ):
                import json
                yield f"data: {json.dumps(event)}\n\n"
            
            yield "data: {\"type\": \"done\"}\n\n"
            
        except ValueError as e:
            # Conversation not found or access denied
            error_event = {"type": "error", "message": str(e)}
            import json
            yield f"data: {json.dumps(error_event)}\n\n"
        except Exception as e:
            logger.error(f"Error in chat stream: {e}")
            error_event = {"type": "error", "message": "Internal server error"}
            import json
            yield f"data: {json.dumps(error_event)}\n\n"
        finally:
            await chat_service.close()
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


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
        # TODO: Implement MCP integration
        # 1. Get available tools based on available_tools parameter
        # 2. Add tools to system prompt
        # 3. Process tool calls if any
        # 4. Return final response
        
        # For now, fall back to direct chat
        response = await direct_chat(chat_request)
        response.tools_used = True if chat_request.available_tools else False
        return response
        
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