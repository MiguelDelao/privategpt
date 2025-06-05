"""
Database models for authentication service
SQLAlchemy models with proper indexing and relationships
"""

from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Text, Integer, Index, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List
import json
import os
import uuid # Added for client IDs

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auth.db")
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Association Table for User-Client Many-to-Many relationship
user_clients_association = Table(
    "user_clients_association",
    Base.metadata,
    Column("user_email", String(255), ForeignKey("users.email"), primary_key=True),
    Column("client_id", String(36), ForeignKey("clients.id"), primary_key=True), # Assuming client.id is UUID string
)

class Client(Base):
    __tablename__ = "clients"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by_email = Column(String(255), ForeignKey("users.email"), nullable=True) # Optional: track who created client
    
    # Relationship to users
    authorized_users = relationship(
        "User",
        secondary=user_clients_association,
        back_populates="authorized_clients"
    )

    def __repr__(self):
        return f"<Client(id='{self.id}', name='{self.name}')>"

class User(Base):
    """User model with legal compliance features"""
    __tablename__ = "users"
    
    # Primary identifiers
    email = Column(String(255), primary_key=True, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # User metadata
    role = Column(String(50), nullable=False, default="user", index=True)
    active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Legal compliance fields
    data_retention_date = Column(DateTime, nullable=True, index=True)
    consent_date = Column(DateTime, nullable=True)
    consent_version = Column(String(10), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), index=True)
    updated_by = Column(String(255), nullable=True)
    last_login = Column(DateTime, nullable=True, index=True)
    
    # Security fields
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    account_locked_until = Column(DateTime, nullable=True, index=True)
    password_changed_at = Column(DateTime, default=func.now(), nullable=False)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)
    
    # Relationship to clients
    authorized_clients = relationship(
        "Client",
        secondary=user_clients_association,
        back_populates="authorized_users",
        lazy="selectin" # Eagerly load clients with the user
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_active_role', 'active', 'role'),
        Index('idx_user_login_attempts', 'failed_login_attempts', 'account_locked_until'),
        Index('idx_user_audit', 'created_at', 'updated_at'),
    )
    
    def is_account_locked(self) -> bool:
        """Check if account is currently locked"""
        if self.account_locked_until:
            return datetime.utcnow() < self.account_locked_until
        return False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "email": self.email,
            "role": self.role,
            "active": self.active,
            "authorized_clients": [{"id": client.id, "name": client.name} for client in self.authorized_clients],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "mfa_enabled": self.mfa_enabled,
            "account_locked": self.is_account_locked()
        }

class LoginSession(Base):
    """Track active login sessions for revocation"""
    __tablename__ = "login_sessions"
    
    session_id = Column(String(255), primary_key=True)
    user_email = Column(String(255), ForeignKey("users.email"), nullable=False, index=True)
    token_jti = Column(String(255), nullable=False, unique=True, index=True)  # JWT ID
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True, index=True)
    last_activity = Column(DateTime, default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_session_user_active', 'user_email', 'revoked_at'),
        Index('idx_session_expiry', 'expires_at', 'revoked_at'),
    )
    
    def is_active(self) -> bool:
        """Check if session is still active"""
        now = datetime.utcnow()
        return (
            self.revoked_at is None and 
            self.expires_at > now
        )

class AuditLog(Base):
    """Audit log for legal compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(100), nullable=False, index=True)
    user_email = Column(String(255), ForeignKey("users.email"), nullable=True, index=True)
    
    # Event details
    message = Column(Text, nullable=False)
    event_data = Column(Text, nullable=True)  # JSON string
    request_id = Column(String(255), nullable=True, index=True)
    
    # Security context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Audit metadata
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    retention_date = Column(DateTime, nullable=True, index=True)
    
    # Indexes for performance and compliance
    __table_args__ = (
        Index('idx_audit_type_user', 'event_type', 'user_email'),
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_retention', 'retention_date'),
    )

class SecurityMetric(Base):
    """Security metrics for monitoring"""
    __tablename__ = "security_metrics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_type = Column(String(100), nullable=False, index=True)
    user_email = Column(String(255), ForeignKey("users.email"), nullable=True, index=True)
    
    # Metric data
    count = Column(Integer, default=1, nullable=False)
    metric_data = Column(Text, nullable=True)  # JSON string (renamed from 'metadata')
    
    # Time buckets for aggregation
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    date_bucket = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    hour_bucket = Column(String(13), nullable=False, index=True)  # YYYY-MM-DD-HH
    
    # Indexes
    __table_args__ = (
        Index('idx_metrics_type_date', 'metric_type', 'date_bucket'),
        Index('idx_metrics_user_type', 'user_email', 'metric_type'),
    )

# Database utility functions
def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_data: dict) -> User:
    """Create new user"""
    # If 'authorized_clients' or similar is passed in user_data, it needs special handling
    # For now, assume client associations are done separately.
    plain_user_data = {k: v for k, v in user_data.items() if k not in ['authorized_clients']}
    user = User(**plain_user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user(db: Session, user: User) -> User:
    """Update existing user"""
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user 