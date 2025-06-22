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
from privategpt.services.gateway.core.exceptions import ChatContextLimitError
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
    
    async def _ensure_user_exists(self, user_id: int) -> None:
        """Ensure user exists in database for foreign key constraint"""
        # For debugging with auth disabled, we'll just use user_id=1
        # In production, proper users would exist from the auth system
        if user_id == 1:
            from sqlalchemy import select, text
            from privategpt.infra.database.models import User
            
            # Use raw SQL to avoid session management issues
            try:
                result = await self.session.execute(
                    text("SELECT id FROM users WHERE id = :user_id"), 
                    {"user_id": user_id}
                )
                existing_user = result.scalar_one_or_none()
                
                if not existing_user:
                    # Create demo user with raw SQL
                    await self.session.execute(
                        text("""
                            INSERT INTO users (id, keycloak_id, email, username, first_name, last_name, role, is_active, created_at, updated_at)
                            VALUES (:user_id, :keycloak_id, :email, :username, :first_name, :last_name, :role, :is_active, :created_at, :updated_at)
                        """),
                        {
                            "user_id": user_id,
                            "keycloak_id": f"demo-user-{user_id}",
                            "email": "admin@admin.com",
                            "username": "admin",
                            "first_name": "Demo",
                            "last_name": "User",
                            "role": "admin",
                            "is_active": True,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    )
                    logger.info(f"Created demo user {user_id} for testing")
            except Exception as e:
                # User might already exist from another request, ignore the error
                logger.debug(f"User creation may have failed (user might exist): {e}")
    
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
        """Send a message and get LLM response with token tracking"""
        
        # Verify conversation exists and user owns it
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("Conversation not found or access denied")
        
        # Determine model to use
        model_to_use = model_name or conversation.model_name or settings.ollama_model
        
        # Get context limit for the model
        context_limit = await self.model_registry.get_context_limit(model_to_use)
        
        # Get provider for token estimation
        provider_name = self.model_registry.get_provider_for_model(model_to_use)
        if not provider_name:
            raise ValueError(f"Model {model_to_use} not available from any provider")
        provider = self.model_registry.providers[provider_name]
        
        # Estimate tokens for new user message
        user_message_tokens = provider.count_tokens(message_content, model_to_use)
        
        # Get system prompt and estimate its tokens
        system_prompt = await self.prompt_manager.get_prompt_for_model(
            model_to_use, conversation_id
        )
        system_prompt_tokens = 0
        if system_prompt:
            system_prompt_tokens = provider.count_tokens(system_prompt, model_to_use)
        
        # Reserve tokens for response
        response_reserve = 1000
        
        # Check if adding this message would exceed context limit
        total_estimated_tokens = (
            conversation.total_tokens +
            user_message_tokens +
            system_prompt_tokens +
            response_reserve
        )
        
        if total_estimated_tokens > context_limit:
            raise ChatContextLimitError(
                f"Adding this message would exceed context limit. "
                f"Current conversation: {conversation.total_tokens} tokens, "
                f"new message: {user_message_tokens} tokens, "
                f"system prompt: {system_prompt_tokens} tokens, "
                f"total would be {total_estimated_tokens} tokens, "
                f"but model {model_to_use} only supports {context_limit} tokens.",
                current_tokens=conversation.total_tokens,
                limit=context_limit,
                model_name=model_to_use
            )
        
        # Get all conversation messages for context
        all_messages = await self.message_repo.get_by_conversation(conversation_id)
        
        # Prepare messages for LLM
        llm_messages = []
        if system_prompt:
            llm_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history
        for msg in all_messages:
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
            chat_response = await self.model_registry.chat(
                model_name=model_to_use,
                messages=llm_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise Exception(f"Failed to get response from LLM: {e}")
        
        # Parse AI response content
        parsed_content = parse_ai_content(
            chat_response.content, 
            settings.enable_thinking_mode
        )
        
        # Create user message with actual input tokens (from chat response)
        user_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=message_content,
            token_count=user_message_tokens,  # Use estimation for user message
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        user_message = await self.message_repo.create(user_message)
        
        # Create assistant message with actual output tokens
        assistant_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="assistant",
            content=parsed_content.processed_content,
            raw_content=parsed_content.raw_content,
            thinking_content=parsed_content.thinking_content,
            token_count=chat_response.output_tokens,
            data={
                "model": chat_response.model,
                "input_tokens": chat_response.input_tokens,
                "output_tokens": chat_response.output_tokens,
                "total_tokens": chat_response.total_tokens,
                "ui_tags": parsed_content.ui_tags
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        assistant_message = await self.message_repo.create(assistant_message)
        
        # Update conversation with actual token usage and timestamp
        conversation.add_message_tokens(chat_response.total_tokens)
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