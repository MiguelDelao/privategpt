from __future__ import annotations

"""
Chat service for handling conversation logic and LLM integration.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.core.domain.conversation import Conversation
from privategpt.core.domain.message import Message
from privategpt.infra.database.conversation_repository import SqlConversationRepository
from privategpt.infra.database.message_repository import SqlMessageRepository
from privategpt.services.gateway.core.mcp_client import get_mcp_client, MCPClientError
from privategpt.services.gateway.core.xml_parser import parse_ai_content
from privategpt.services.gateway.core.prompt_manager import PromptManager
from privategpt.services.llm.core.model_registry import get_model_registry
from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chat conversations and LLM interactions"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_repo = SqlConversationRepository(session)
        self.message_repo = SqlMessageRepository(session)
        self.prompt_manager = PromptManager(session)
        self.model_registry = get_model_registry()
        self.mcp_client = None  # Lazy-loaded
    
    async def create_conversation(
        self, 
        user_id: int, 
        title: str,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """Create a new conversation"""
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            status="active",
            model_name=model_name,
            system_prompt=system_prompt,
            data=data or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return await self.conversation_repo.create(conversation)
    
    async def get_conversation(self, conversation_id: str, user_id: int) -> Optional[Conversation]:
        """Get a conversation, ensuring user owns it"""
        conversation = await self.conversation_repo.get(conversation_id)
        if not conversation or conversation.user_id != user_id:
            return None
        return conversation
    
    async def list_user_conversations(
        self, 
        user_id: int, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Conversation]:
        """List conversations for a user"""
        return await self.conversation_repo.get_by_user(user_id, limit, offset)
    
    async def send_message(
        self,
        conversation_id: str,
        user_id: int,
        message_content: str,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> tuple[Message, Message]:
        """Send a message and get LLM response"""
        
        # Verify conversation exists and user owns it
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("Conversation not found or access denied")
        
        # Create user message
        user_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=message_content,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        user_message = await self.message_repo.create(user_message)
        
        # Get conversation context (recent messages)
        recent_messages = await self.message_repo.get_latest_by_conversation(
            conversation_id, count=20
        )
        
        # Get appropriate system prompt
        system_prompt = await self.prompt_manager.get_prompt_for_model(
            model_name or conversation.model_name or settings.ollama_model,
            conversation_id
        )
        
        # Get MCP tools if enabled
        tools = []
        if settings.mcp_enabled:
            try:
                if not self.mcp_client:
                    self.mcp_client = await get_mcp_client()
                tools = self.mcp_client.format_tools_for_ollama()
            except MCPClientError as e:
                logger.warning(f"MCP not available: {e}")
        
        # Prepare messages for LLM
        llm_messages = []
        if system_prompt:
            llm_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add recent conversation history
        for msg in recent_messages:
            llm_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add the new user message
        llm_messages.append({
            "role": "user",
            "content": message_content
        })
        
        # Call LLM through model registry
        try:
            response_text = await self.model_registry.chat(
                model_name=model_name or conversation.model_name or settings.ollama_model,
                messages=llm_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            llm_response = {
                "text": response_text,
                "model": model_name or conversation.model_name or settings.ollama_model,
                "response_time_ms": 0  # TODO: Add timing
            }
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise Exception(f"Failed to get response from LLM: {e}")
        
        # TODO: Tool calls will be handled by MCP integration in future updates
        
        # Parse AI response content
        parsed_content = parse_ai_content(
            llm_response["text"], 
            settings.enable_thinking_mode
        )
        
        # Create assistant message
        assistant_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="assistant",
            content=parsed_content.processed_content,
            raw_content=parsed_content.raw_content,
            thinking_content=parsed_content.thinking_content,
            data={
                "model": llm_response["model"],
                "response_time_ms": llm_response.get("response_time_ms"),
                "ui_tags": parsed_content.ui_tags,
                "has_tool_calls": "tool_calls" in llm_response
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assistant_message = await self.message_repo.create(assistant_message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        await self.conversation_repo.update(conversation)
        
        return user_message, assistant_message
    
    async def stream_message(
        self,
        conversation_id: str,
        user_id: int,
        message_content: str,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Send a message and stream LLM response"""
        
        # Verify conversation exists and user owns it
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("Conversation not found or access denied")
        
        # Create user message
        user_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=message_content,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        user_message = await self.message_repo.create(user_message)
        
        yield {
            "type": "user_message",
            "message": {
                "id": user_message.id,
                "role": user_message.role,
                "content": user_message.content,
                "created_at": user_message.created_at.isoformat()
            }
        }
        
        # Get conversation context
        recent_messages = await self.message_repo.get_latest_by_conversation(
            conversation_id, count=20
        )
        
        # Prepare messages for LLM
        llm_messages = []
        if conversation.system_prompt:
            llm_messages.append({
                "role": "system",
                "content": conversation.system_prompt
            })
        
        for msg in recent_messages:
            llm_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        llm_messages.append({
            "role": "user",
            "content": message_content
        })
        
        # Stream from LLM service
        assistant_message_id = str(uuid.uuid4())
        response_content = ""
        
        yield {
            "type": "assistant_message_start",
            "message_id": assistant_message_id
        }
        
        try:
            async for chunk in self.model_registry.chat_stream(
                model_name=model_name or conversation.model_name or settings.ollama_model,
                messages=llm_messages,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                response_content += chunk
                yield {
                    "type": "content_chunk",
                    "message_id": assistant_message_id,
                    "content": chunk
                }
            
            # Create assistant message in database
            assistant_message = Message(
                id=assistant_message_id,
                conversation_id=conversation_id,
                role="assistant",
                content=response_content,
                data={
                    "model": model_name or conversation.model_name or settings.ollama_model
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            assistant_message = await self.message_repo.create(assistant_message)
            
            yield {
                "type": "assistant_message_complete",
                "message": {
                    "id": assistant_message.id,
                    "role": assistant_message.role,
                    "content": assistant_message.content,
                    "created_at": assistant_message.created_at.isoformat()
                }
            }
            
            # Update conversation timestamp
            conversation.updated_at = datetime.utcnow()
            await self.conversation_repo.update(conversation)
            
        except Exception as e:
            logger.error(f"Error streaming from LLM service: {e}")
            yield {
                "type": "error",
                "message": "Failed to get response from LLM service"
            }
    
    async def close(self):
        """Close resources"""
        if self.mcp_client:
            await self.mcp_client.close()