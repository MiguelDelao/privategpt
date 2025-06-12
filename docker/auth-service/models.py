"""
Database models for PrivateGPT Legal AI Authentication Service
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Table, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import os
import json

Base = declarative_base()

# Association table for many-to-many relationship between users and clients
user_clients_association = Table(
    'user_clients',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('client_id', Integer, ForeignKey('clients.id'), primary_key=True)
)

class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")  # user, admin, partner
    
    # Profile information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Legal practice information
    bar_number = Column(String(50), nullable=True)
    practice_areas = Column(Text, nullable=True)  # JSON string
    client_matters = Column(Text, nullable=True)  # JSON string of accessible matters
    
    # Security settings
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(DateTime, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    login_sessions = relationship("LoginSession", back_populates="user", cascade="all, delete-orphan")
    clients = relationship("Client", secondary=user_clients_association, back_populates="users")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_role', 'role'),
        Index('idx_user_active', 'is_active'),
        Index('idx_user_audit', 'created_at', 'updated_at'),
    )
    
    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "bar_number": self.bar_number,
            "practice_areas": json.loads(self.practice_areas) if self.practice_areas else [],
            "client_matters": json.loads(self.client_matters) if self.client_matters else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "login_count": self.login_count
        }

class LoginSession(Base):
    """Login session tracking for security and compliance"""
    __tablename__ = "login_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Session lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Security tracking
    login_method = Column(String(50), default="password", nullable=False)  # password, sso, etc.
    logout_reason = Column(String(100), nullable=True)  # manual, timeout, forced
    
    # Relationship
    user = relationship("User", back_populates="login_sessions")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_token', 'session_token'),
        Index('idx_session_user', 'user_id'),
        Index('idx_session_active', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
    )

# AuditLog model removed - using structured logging instead

class SecurityMetric(Base):
    """Security metrics for monitoring and compliance"""
    __tablename__ = "security_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Metric information
    metric_type = Column(String(100), nullable=False)  # failed_logins, suspicious_activity, etc.
    metric_value = Column(Integer, default=0, nullable=False)
    
    # Context
    user_email = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    details = Column(Text, nullable=True)  # JSON string
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    window_start = Column(DateTime, nullable=True)  # For time-windowed metrics
    window_end = Column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_metric_type', 'metric_type'),
        Index('idx_metric_timestamp', 'timestamp'),
        Index('idx_metric_user', 'user_email'),
    )

class Client(Base):
    """Client information for matter-based access control"""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Client information
    name = Column(String(255), nullable=False)
    client_code = Column(String(50), unique=True, nullable=False)
    
    # Contact information
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    
    # Business information
    industry = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    users = relationship("User", secondary=user_clients_association, back_populates="clients")
    
    # Indexes
    __table_args__ = (
        Index('idx_client_code', 'client_code'),
        Index('idx_client_active', 'is_active'),
    )

# Database setup
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://privategpt:secure_password_change_me@auth-postgres:5432/privategpt_auth"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Database dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine) 