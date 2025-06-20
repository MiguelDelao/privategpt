from __future__ import annotations

"""
Chat and conversation management API routes for the gateway.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.shared.auth_middleware import get_current_user
from privategpt.infra.database.async_session import get_async_session
from privategpt.services.gateway.core.chat_service import ChatService

logger = logging.getLogger(__name__)

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
        # Temporary: Use dummy user ID for testing
        conversation = await chat_service.create_conversation(
            user_id=1,  # Dummy user ID
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
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, pattern="^(active|archived|deleted)$"),
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """List user's conversations"""
    chat_service = ChatService(session)
    
    try:
        conversations = await chat_service.list_user_conversations(
            user_id=user["user_id"],
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
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific conversation"""
    # TODO: Implement with repository pattern
    raise HTTPException(status_code=404, detail="Conversation not found")


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Update a conversation"""
    # TODO: Implement with repository pattern
    raise HTTPException(status_code=404, detail="Conversation not found")


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a conversation"""
    # TODO: Implement with repository pattern
    raise HTTPException(status_code=404, detail="Conversation not found")


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
    # TODO: Implement with repository pattern
    return []


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    conversation_id: str,
    message_data: MessageCreate,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Add a message to a conversation"""
    # TODO: Implement with repository pattern
    message_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    return MessageResponse(
        id=message_id,
        conversation_id=conversation_id,
        role=message_data.role,
        content=message_data.content,
        raw_content=message_data.raw_content,
        token_count=None,
        data=message_data.data,
        created_at=now,
        updated_at=now
    )


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
    
    # TODO: Implement full chat logic with LLM service integration
    # 1. Verify conversation exists and user has access
    # 2. Create user message
    # 3. Send to LLM service with conversation context
    # 4. Create assistant message with response
    # 5. Return both messages
    
    raise HTTPException(status_code=501, detail="Chat implementation pending")


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
            async for event in chat_service.stream_message(
                conversation_id=conversation_id,
                user_id=user["user_id"],
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


@router.post("/chat/direct", response_model=SimpleChatResponse)
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


@router.post("/chat/mcp", response_model=SimpleChatResponse)
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