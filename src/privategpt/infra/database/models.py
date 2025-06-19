from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey, Index, JSON, Text
from sqlalchemy.orm import declarative_base

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
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


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