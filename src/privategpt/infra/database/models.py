from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey, Index, JSON, Text, Float, Enum
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    keycloak_id = Column(String(255), unique=True, index=True, nullable=True)  # Keycloak user ID
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)  # Legacy field, nullable for Keycloak users
    role = Column(String(50), nullable=False, default="user")
    is_active = Column(Boolean, default=True, nullable=False)
    preferences = Column(JSON, nullable=True, default=dict)  # User app preferences
    session_metadata = Column(JSON, nullable=True, default=dict)  # Session state and metadata
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    error = Column(String(1024), nullable=True)
    task_id = Column(String(255), nullable=True, index=True)


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    # store embedding as JSON string for simplicity; real impl may use vector type
    embedding = Column(String, nullable=True)

Index("idx_chunk_doc_pos", Chunk.document_id, Chunk.position)


# Enums for chat and tool functionality
class MessageRole(enum.Enum):
    """Message roles in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ToolCallStatus(enum.Enum):
    """Tool call execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConversationStatus(enum.Enum):
    """Conversation status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


# Chat and conversation models
class Conversation(Base):
    """Conversation/chat session between user and assistant"""
    __tablename__ = "conversations"

    id = Column(String(255), primary_key=True, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    status = Column(Enum(ConversationStatus), nullable=False, default=ConversationStatus.ACTIVE)
    model_name = Column(String(100), nullable=True)  # LLM model used
    system_prompt = Column(Text, nullable=True)  # Custom system prompt
    data = Column(JSON, nullable=True, default=dict)  # Conversation metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    """Individual message in a conversation"""
    __tablename__ = "messages"

    id = Column(String(255), primary_key=True, index=True)  # UUID
    conversation_id = Column(String(255), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    raw_content = Column(Text, nullable=True)  # Original unprocessed content
    token_count = Column(Integer, nullable=True)  # Token count for this message
    data = Column(JSON, nullable=True, default=dict)  # Message metadata (sources, etc.)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    tool_calls = relationship("ToolCall", back_populates="message", cascade="all, delete-orphan")


class ToolCall(Base):
    """Tool/function call within a message"""
    __tablename__ = "tool_calls"

    id = Column(String(255), primary_key=True, index=True)  # UUID
    message_id = Column(String(255), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # Tool/function name
    parameters = Column(JSON, nullable=True, default=dict)  # Tool parameters
    result = Column(Text, nullable=True)  # Tool execution result
    error_message = Column(Text, nullable=True)  # Error message if failed
    status = Column(Enum(ToolCallStatus), nullable=False, default=ToolCallStatus.PENDING)
    execution_time_ms = Column(Integer, nullable=True)  # Execution time in milliseconds
    data = Column(JSON, nullable=True, default=dict)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    message = relationship("Message", back_populates="tool_calls")


class ModelUsage(Base):
    """Model usage tracking for conversations"""
    __tablename__ = "model_usage"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(255), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(String(255), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True, index=True)
    model_name = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=True)  # e.g., "ollama", "openai"
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)  # Cost in USD
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Indexes for performance
Index("idx_conversation_user_updated", Conversation.user_id, Conversation.updated_at.desc())
Index("idx_message_conversation_created", Message.conversation_id, Message.created_at)
Index("idx_tool_call_message_status", ToolCall.message_id, ToolCall.status)
Index("idx_model_usage_conversation", ModelUsage.conversation_id, ModelUsage.created_at.desc()) 