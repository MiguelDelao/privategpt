from __future__ import annotations

"""
System prompt management API routes.
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.shared.auth_middleware import get_current_user, get_admin_user
from privategpt.infra.database.async_session import get_async_session
from privategpt.services.gateway.core.prompt_manager import PromptManager
from privategpt.infra.database.models import SystemPrompt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


# Pydantic models for API
class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    model_pattern: Optional[str] = Field(None, max_length=255)
    prompt_xml: str = Field(..., min_length=1)
    description: Optional[str] = None
    is_default: bool = Field(default=False)


class PromptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    model_pattern: Optional[str] = Field(None, max_length=255)
    prompt_xml: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class PromptResponse(BaseModel):
    id: int
    name: str
    model_pattern: Optional[str]
    prompt_xml: str
    description: Optional[str]
    is_active: bool
    is_default: bool
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


class PromptTestRequest(BaseModel):
    prompt_xml: str
    model_name: str = Field(default="privategpt-mcp")
    test_message: str = Field(default="Hello, please introduce yourself.")


@router.get("/", response_model=List[PromptResponse])
async def list_prompts(
    user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_async_session)
):
    """List all system prompts (admin only)"""
    prompt_manager = PromptManager(session)
    prompts = await prompt_manager.list_prompts()
    
    return [
        PromptResponse(
            id=prompt.id,
            name=prompt.name,
            model_pattern=prompt.model_pattern,
            prompt_xml=prompt.prompt_xml,
            description=prompt.description,
            is_active=prompt.is_active,
            is_default=prompt.is_default,
            metadata=prompt.metadata or {},
            created_at=prompt.created_at.isoformat(),
            updated_at=prompt.updated_at.isoformat()
        )
        for prompt in prompts
    ]


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: int,
    user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific prompt by ID (admin only)"""
    prompt_manager = PromptManager(session)
    prompts = await prompt_manager.list_prompts()
    
    prompt = next((p for p in prompts if p.id == prompt_id), None)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    return PromptResponse(
        id=prompt.id,
        name=prompt.name,
        model_pattern=prompt.model_pattern,
        prompt_xml=prompt.prompt_xml,
        description=prompt.description,
        is_active=prompt.is_active,
        is_default=prompt.is_default,
        metadata=prompt.metadata or {},
        created_at=prompt.created_at.isoformat(),
        updated_at=prompt.updated_at.isoformat()
    )


@router.post("/", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt_data: PromptCreate,
    user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new system prompt (admin only)"""
    prompt_manager = PromptManager(session)
    
    try:
        prompt = await prompt_manager.create_prompt(
            name=prompt_data.name,
            prompt_xml=prompt_data.prompt_xml,
            model_pattern=prompt_data.model_pattern,
            description=prompt_data.description,
            is_default=prompt_data.is_default
        )
        
        return PromptResponse(
            id=prompt.id,
            name=prompt.name,
            model_pattern=prompt.model_pattern,
            prompt_xml=prompt.prompt_xml,
            description=prompt.description,
            is_active=prompt.is_active,
            is_default=prompt.is_default,
            metadata=prompt.metadata or {},
            created_at=prompt.created_at.isoformat(),
            updated_at=prompt.updated_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating prompt: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: int,
    update_data: PromptUpdate,
    user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Update a system prompt (admin only)"""
    prompt_manager = PromptManager(session)
    
    try:
        # Filter out None values
        updates = {k: v for k, v in update_data.model_dump().items() if v is not None}
        
        prompt = await prompt_manager.update_prompt(prompt_id, **updates)
        
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        return PromptResponse(
            id=prompt.id,
            name=prompt.name,
            model_pattern=prompt.model_pattern,
            prompt_xml=prompt.prompt_xml,
            description=prompt.description,
            is_active=prompt.is_active,
            is_default=prompt.is_default,
            metadata=prompt.metadata or {},
            created_at=prompt.created_at.isoformat(),
            updated_at=prompt.updated_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error updating prompt: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: int,
    user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a system prompt (admin only)"""
    prompt_manager = PromptManager(session)
    
    success = await prompt_manager.delete_prompt(prompt_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Prompt not found")


@router.get("/for-model/{model_name}")
async def get_prompt_for_model(
    model_name: str,
    conversation_id: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get the system prompt that would be used for a specific model"""
    prompt_manager = PromptManager(session)
    
    prompt = await prompt_manager.get_prompt_for_model(
        model_name=model_name,
        conversation_id=conversation_id
    )
    
    return {
        "model_name": model_name,
        "conversation_id": conversation_id,
        "prompt": prompt
    }


@router.post("/test")
async def test_prompt(
    test_data: PromptTestRequest,
    user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Test a prompt with a sample message (admin only)"""
    from privategpt.services.gateway.core.chat_service import ChatService
    
    try:
        # Create a temporary conversation for testing
        chat_service = ChatService(session)
        
        conversation = await chat_service.create_conversation(
            user_id=user["user_id"],
            title="Prompt Test",
            model_name=test_data.model_name,
            system_prompt=test_data.prompt_xml
        )
        
        try:
            # Send test message
            user_msg, assistant_msg = await chat_service.send_message(
                conversation_id=conversation.id,
                user_id=user["user_id"],
                message_content=test_data.test_message,
                model_name=test_data.model_name
            )
            
            # Clean up - delete test conversation
            await chat_service.conversation_repo.delete(conversation.id)
            
            return {
                "success": True,
                "test_message": test_data.test_message,
                "model_response": assistant_msg.content,
                "thinking": assistant_msg.thinking_content if assistant_msg.thinking_content else None,
                "ui_tags": assistant_msg.data.get("ui_tags", {}),
                "model_used": test_data.model_name
            }
            
        except Exception as e:
            # Clean up on error
            await chat_service.conversation_repo.delete(conversation.id)
            raise e
        finally:
            await chat_service.close()
        
    except Exception as e:
        logger.error(f"Error testing prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Prompt test failed: {str(e)}")


@router.post("/initialize-defaults")
async def initialize_default_prompts(
    user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Initialize default prompts from config (admin only)"""
    prompt_manager = PromptManager(session)
    
    try:
        await prompt_manager.initialize_default_prompts()
        return {"message": "Default prompts initialized successfully"}
    except Exception as e:
        logger.error(f"Error initializing default prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))