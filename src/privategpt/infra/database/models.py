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


class Collection(Base):
    """Hierarchical collections/folders for document organization"""
    __tablename__ = "collections"
    
    id = Column(String(255), primary_key=True, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(String(255), ForeignKey("collections.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    collection_type = Column(String(50), nullable=False, default="folder")  # 'collection' for root, 'folder' for nested
    icon = Column(String(50), nullable=False, default="📁")
    color = Column(String(7), nullable=False, default="#3B82F6")
    path = Column(String(1024), nullable=False)  # Full path like /Cases/Smith v Jones
    depth = Column(Integer, nullable=False, default=0)
    settings = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="collections")
    parent = relationship("Collection", remote_side=[id], backref="children")
    documents = relationship("Document", back_populates="collection", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_collection_user_parent", "user_id", "parent_id", "name", unique=True),
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(String(255), ForeignKey("collections.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    error = Column(String(1024), nullable=True)
    task_id = Column(String(255), nullable=True, index=True)
    processing_progress = Column(JSON, nullable=True, default=dict)
    doc_metadata = Column(JSON, nullable=True, default=dict)
    
    # Relationships
    collection = relationship("Collection", back_populates="documents")
    user = relationship("User", backref="documents")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(String(255), ForeignKey("collections.id", ondelete="CASCADE"), nullable=True, index=True)
    position = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    # store embedding as JSON string for simplicity; real impl may use vector type
    embedding = Column(String, nullable=True)
    
    # Relationships
    collection = relationship("Collection", backref="chunks")

Index("idx_chunk_doc_pos", Chunk.document_id, Chunk.position)
Index("idx_chunk_collection", Chunk.collection_id)


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
    status = Column(String(20), nullable=False, default="active")
    model_name = Column(String(100), nullable=True)  # LLM model used
    system_prompt = Column(Text, nullable=True)  # Custom system prompt
    data = Column(JSON, nullable=True, default=dict)  # Conversation metadata
    total_tokens = Column(Integer, nullable=False, default=0)  # Total tokens used in conversation
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
    content = Column(Text, nullable=False)  # Processed content for UI (thinking stripped)
    raw_content = Column(Text, nullable=True)  # Original unprocessed content with thinking
    thinking_content = Column(Text, nullable=True)  # Extracted thinking content for debug
    ui_tags = Column(JSON, nullable=True, default=dict)  # Parsed XML tags for UI rendering
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


class SystemPrompt(Base):
    """System prompt templates for different models and use cases"""
    __tablename__ = "system_prompts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    model_pattern = Column(String(255), nullable=True)  # e.g., "ollama:*", "privategpt-mcp"
    prompt_xml = Column(Text, nullable=False)  # XML-structured prompt
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    data = Column(JSON, nullable=True, default=dict)  # Additional config
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# Indexes for performance
Index("idx_conversation_user_updated", Conversation.user_id, Conversation.updated_at.desc())
Index("idx_message_conversation_created", Message.conversation_id, Message.created_at)
Index("idx_tool_call_message_status", ToolCall.message_id, ToolCall.status)
Index("idx_model_usage_conversation", ModelUsage.conversation_id, ModelUsage.created_at.desc())
Index("idx_system_prompt_active", SystemPrompt.is_active, SystemPrompt.name)
Index("idx_system_prompt_pattern", SystemPrompt.model_pattern, SystemPrompt.is_active)

# Collection indexes
Index("idx_collection_path", Collection.path)
Index("idx_collection_parent", Collection.parent_id)
Index("idx_collection_user", Collection.user_id)
Index("idx_document_collection", Document.collection_id) 