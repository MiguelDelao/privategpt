"""
Base client model shared across services
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..base import Base

# Association table for many-to-many relationship between users and clients
user_clients_association = Table(
    'user_clients',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('client_id', Integer, ForeignKey('clients.id'), primary_key=True)
)

class Client(Base):
    """Base client model with only fields actually used across services"""
    __tablename__ = "clients"
    
    # Core fields
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    client_code = Column(String(50), unique=True, nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships - will be set up after import
    # users = relationship("User", secondary=user_clients_association, back_populates="clients")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_client_code', 'client_code'),
        Index('idx_client_active', 'is_active'),
    )
    
    def to_dict(self):
        """Convert client to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "client_code": self.client_code,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        """String representation of client"""
        return f"<Client {self.client_code}>" 