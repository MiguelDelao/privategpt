"""
Tests for database models
"""

import pytest
from datetime import datetime
from models import User, Client

def test_user_creation(db_session):
    """Test user creation and retrieval"""
    # Create user
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        role="user"
    )
    
    # Save to database
    db_session.add(user)
    db_session.commit()
    
    # Retrieve user
    saved_user = db_session.query(User).filter_by(email="test@example.com").first()
    
    # Assertions
    assert saved_user is not None
    assert saved_user.email == "test@example.com"
    assert saved_user.role == "user"
    assert saved_user.is_active is True
    assert isinstance(saved_user.created_at, datetime)
    assert isinstance(saved_user.updated_at, datetime)

def test_user_to_dict(db_session):
    """Test user dictionary conversion"""
    # Create user
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        role="admin"
    )
    
    # Convert to dictionary
    user_dict = user.to_dict()
    
    # Assertions
    assert user_dict["email"] == "test@example.com"
    assert user_dict["role"] == "admin"
    assert user_dict["is_active"] is True
    assert "created_at" in user_dict

def test_client_creation(db_session):
    """Test client creation and retrieval"""
    # Create client
    client = Client(
        name="Test Client",
        client_code="TEST001"
    )
    
    # Save to database
    db_session.add(client)
    db_session.commit()
    
    # Retrieve client
    saved_client = db_session.query(Client).filter_by(client_code="TEST001").first()
    
    # Assertions
    assert saved_client is not None
    assert saved_client.name == "Test Client"
    assert saved_client.client_code == "TEST001"
    assert saved_client.is_active is True
    assert isinstance(saved_client.created_at, datetime)
    assert isinstance(saved_client.updated_at, datetime)

def test_client_to_dict(db_session):
    """Test client dictionary conversion"""
    # Create client
    client = Client(
        name="Test Client",
        client_code="TEST001"
    )
    
    # Convert to dictionary
    client_dict = client.to_dict()
    
    # Assertions
    assert client_dict["name"] == "Test Client"
    assert client_dict["client_code"] == "TEST001"
    assert client_dict["is_active"] is True
    assert "created_at" in client_dict
    assert "updated_at" in client_dict

def test_user_client_relationship(db_session):
    """Test many-to-many relationship between users and clients"""
    # Create user
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        role="user"
    )
    
    # Create client
    client = Client(
        name="Test Client",
        client_code="TEST001"
    )
    
    # Add client to user
    user.clients.append(client)
    
    # Save to database
    db_session.add(user)
    db_session.commit()
    
    # Retrieve user
    saved_user = db_session.query(User).filter_by(email="test@example.com").first()
    
    # Assertions
    assert len(saved_user.clients) == 1
    assert saved_user.clients[0].client_code == "TEST001"
    
    # Retrieve client
    saved_client = db_session.query(Client).filter_by(client_code="TEST001").first()
    
    # Assertions
    assert len(saved_client.users) == 1
    assert saved_client.users[0].email == "test@example.com" 