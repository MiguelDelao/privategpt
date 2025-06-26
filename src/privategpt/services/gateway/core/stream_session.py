from __future__ import annotations

"""
Stream session management for conversation streaming.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from privategpt.infra.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class StreamSession:
    """Represents a streaming session with all necessary data"""
    
    def __init__(
        self,
        token: str,
        conversation_id: str,
        user_id: int,
        user_message_id: str,
        assistant_message_id: str,
        llm_messages: List[Dict[str, str]],
        model_name: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        tools_enabled: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        auto_approve_tools: bool = False
    ):
        self.token = token
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.user_message_id = user_message_id
        self.assistant_message_id = assistant_message_id
        self.llm_messages = llm_messages
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.tools_enabled = tools_enabled
        self.tools = tools or []
        self.auto_approve_tools = auto_approve_tools
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        return {
            "token": self.token,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "user_message_id": self.user_message_id,
            "assistant_message_id": self.assistant_message_id,
            "llm_messages": self.llm_messages,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt,
            "tools_enabled": self.tools_enabled,
            "tools": self.tools,
            "auto_approve_tools": self.auto_approve_tools,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StreamSession:
        """Create from dictionary retrieved from Redis"""
        # Remove created_at from data and use it separately
        created_at_str = data.pop("created_at", None)
        instance = cls(**data)
        if created_at_str:
            instance.created_at = datetime.fromisoformat(created_at_str)
        return instance


class StreamSessionManager:
    """Manages stream sessions in Redis"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.default_ttl = 300  # 5 minutes
    
    async def create_session(
        self,
        conversation_id: str,
        user_id: int,
        user_message_id: str,
        llm_messages: List[Dict[str, str]],
        model_name: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        tools_enabled: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        auto_approve_tools: bool = False
    ) -> StreamSession:
        """Create a new stream session and store in Redis"""
        
        # Generate unique token and assistant message ID
        token = str(uuid.uuid4())
        assistant_message_id = str(uuid.uuid4())
        
        # Create session
        session = StreamSession(
            token=token,
            conversation_id=conversation_id,
            user_id=user_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            llm_messages=llm_messages,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            tools_enabled=tools_enabled,
            tools=tools,
            auto_approve_tools=auto_approve_tools
        )
        
        # Store in Redis
        await self.redis_client.set_stream_session(
            token=token,
            data=session.to_dict(),
            ttl=self.default_ttl
        )
        
        logger.info(f"Created stream session {token} for conversation {conversation_id}")
        return session
    
    async def get_session(self, token: str) -> Optional[StreamSession]:
        """Retrieve stream session from Redis"""
        data = await self.redis_client.get_stream_session(token)
        if data:
            # Extend TTL when accessed
            await self.redis_client.extend_stream_session(token, self.default_ttl)
            return StreamSession.from_dict(data)
        return None
    
    async def delete_session(self, token: str) -> None:
        """Delete stream session from Redis"""
        await self.redis_client.delete_stream_session(token)
        logger.info(f"Deleted stream session {token}")
    
    async def validate_session(self, token: str, user_id: Optional[int] = None) -> bool:
        """Validate that session exists and optionally check user ownership"""
        session = await self.get_session(token)
        if not session:
            return False
        
        if user_id is not None and session.user_id != user_id:
            logger.warning(f"User {user_id} attempted to access session owned by {session.user_id}")
            return False
        
        return True