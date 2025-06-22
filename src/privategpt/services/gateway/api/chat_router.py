from __future__ import annotations

"""
Chat and conversation management API routes for the gateway.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.shared.auth_middleware import get_current_user
from fastapi import Depends
from typing import Optional
from privategpt.infra.database.async_session import get_async_session
from privategpt.services.gateway.core.chat_service import ChatService
from privategpt.services.gateway.core.exceptions import ChatContextLimitError
from privategpt.infra.database.models import User
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def get_user_safe(request: Request) -> Dict[str, Any]:
    """Get current user, handling auth disabled case"""
    try:
        # Check if auth middleware set user in request state
        user = getattr(request.state, 'user', None)
        if user:
            return user
        else:
            # Auth is disabled, return dummy user
            return {"user_id": None, "email": "admin@admin.com", "username": "admin"}
    except Exception:
        # Auth is disabled, return dummy user
        return {"user_id": None, "email": "admin@admin.com", "username": "admin"}


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
    
    user_id = user_claims.get("user_id")
    
    # Check if user exists
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        return existing_user.id
    
    # Create new user
    new_user = User(
        id=user_id,
        keycloak_id=user_claims.get("sub"),
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
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new conversation"""
    chat_service = ChatService(session)
    
    try:
        # Use demo user ID 1 when auth is disabled
        user_id = 1
        
        conversation = await chat_service.create_conversation(
            user_id=user_id,
            title=conversation_data.title,
            model_name=conversation_data.model_name,
            system_prompt=conversation_data.system_prompt,
            data=conversation_data.data
        )
        
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


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, pattern="^(active|archived|deleted)$"),
    session: AsyncSession = Depends(get_async_session)
):
    """List user's conversations"""
    chat_service = ChatService(session)
    
    try:
        # Get user safely (handles auth disabled case)
        user = await get_user_safe(request)
        # Ensure user exists in database (auto-create if needed)
        user_id = await ensure_user_exists(session, user)
        
        conversations = await chat_service.list_user_conversations(
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
    finally:
        await chat_service.close()


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific conversation"""
    chat_service = ChatService(session)
    
    try:
        # Get user safely (handles auth disabled case)
        user = await get_user_safe(request)
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
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """Update a conversation"""
    chat_service = ChatService(session)
    
    try:
        # Get user safely (handles auth disabled case)
        user = await get_user_safe(request)
        # Ensure user exists in database (auto-create if needed)
        user_id = await ensure_user_exists(session, user)
        
        # Get existing conversation
        conversation = await chat_service.get_conversation(conversation_id, user_id)
        if not conversation:
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
        updated_conversation = await chat_service.conversation_repo.update(conversation)
        
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
    finally:
        await chat_service.close()


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a conversation"""
    chat_service = ChatService(session)
    
    try:
        # Get user safely (handles auth disabled case)
        user = await get_user_safe(request)
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
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """Get messages for a conversation"""
    chat_service = ChatService(session)
    
    try:
        # Get user safely (handles auth disabled case)
        user = await get_user_safe(request)
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
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """Add a message to a conversation"""
    chat_service = ChatService(session)
    
    try:
        # Get user safely (handles auth disabled case)
        user = await get_user_safe(request)
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
    # user: Dict[str, Any] = Depends(get_user_safe),  # Auth disabled for testing
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
        # Use hardcoded user ID for testing (auth disabled)
        user_id = 1
        
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
        raise HTTPException(
            status_code=413,  # Payload Too Large
            detail={
                "error": "context_limit_exceeded",
                "message": str(e),
                "current_tokens": e.current_tokens,
                "limit": e.limit,
                "model_name": e.model_name,
                "suggestions": [
                    "Start a new conversation",
                    f"Use a model with larger context (current: {e.limit} tokens)",
                    "Shorten your message"
                ]
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat request")
    finally:
        await chat_service.close()


@router.post("/conversations/{conversation_id}/chat/stream")
async def stream_chat_with_conversation(
    conversation_id: str,
    chat_request: ChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """Stream chat response for a conversation"""
    
    async def stream_generator():
        chat_service = ChatService(session)
        
        try:
            # Get user safely (handles auth disabled case)
            user = await get_user_safe(request)
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
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """Quick chat that automatically creates a conversation"""
    # TODO: Implement quick chat logic
    # 1. Create new conversation with auto-generated title
    # 2. Process chat request
    # 3. Return conversation_id and messages
    
    raise HTTPException(status_code=501, detail="Quick chat implementation pending")


# Test endpoints for debugging - NO AUTH
@router.get("/debug/conversations")
async def debug_list_conversations(session: AsyncSession = Depends(get_async_session)):
    """Debug conversations list without auth"""
    chat_service = ChatService(session)
    try:
        conversations = await chat_service.list_user_conversations(user_id=1, limit=50, offset=0)
        return [{"id": c.id, "title": c.title, "status": c.status} for c in conversations]
    finally:
        await chat_service.close()

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
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    except Exception as e:
        logger.error(f"Direct chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
        raise HTTPException(status_code=500, detail="Internal server error")


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
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
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
        raise HTTPException(status_code=500, detail="Internal server error")


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
        raise HTTPException(status_code=500, detail="Internal server error")


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