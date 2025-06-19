"""
Database models package initialization
"""

from sqlalchemy.orm import relationship
from .user import User
from .client import Client, user_clients_association

# Set up relationships after both models are imported
User.clients = relationship("Client", secondary=user_clients_association, back_populates="users")
Client.users = relationship("User", secondary=user_clients_association, back_populates="clients")

__all__ = ['User', 'Client', 'user_clients_association'] 