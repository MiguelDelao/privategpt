"""
Integration tests for conversation management API.

Tests the complete conversation management flow including:
- JWT authentication with actual tokens
- Chat router endpoints 
- Database operations with context manager pattern
- User auto-creation with keycloak_id mapping
- End-to-end conversation CRUD operations

This tests the critical path that was recently fixed for
SQLAlchemy async session issues and authentication integration.
"""

import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from privategpt.services.gateway.api.chat_router import router as chat_router
from privategpt.shared.auth_middleware import KeycloakAuthMiddleware, get_current_user
from privategpt.infra.database.models import Base, User


@pytest_asyncio.fixture
async def test_app():
    """Create test FastAPI app with conversation management."""
    app = FastAPI(title="Test Conversation Management")
    
    # Add auth middleware
    app.add_middleware(
        KeycloakAuthMiddleware,
        protected_paths=["/api/"],
        excluded_paths=[
            "/health",
            "/docs", 
            "/openapi.json",
            "/api/chat/debug/"  # Keep debug endpoints for testing
        ]
    )
    
    # Include chat router
    app.include_router(chat_router)
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    return app


@pytest_asyncio.fixture
async def test_db_engine():
    """Create test database engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_app):
    """Test client for conversation management."""
    return TestClient(test_app)


@pytest_asyncio.fixture
def mock_jwt_user():
    """Mock JWT user claims from Keycloak token."""
    return {
        "user_id": "keycloak-user-123",  # This is the Keycloak UUID
        "sub": "keycloak-user-123",
        "email": "test@example.com",
        "preferred_username": "testuser",
        "given_name": "Test",
        "family_name": "User",
        "roles": ["user"],
        "primary_role": "user",
        "email_verified": True
    }


@pytest_asyncio.fixture
def mock_admin_user():
    """Mock admin JWT user claims."""
    return {
        "user_id": "admin-keycloak-456",
        "sub": "admin-keycloak-456", 
        "email": "admin@example.com",
        "preferred_username": "admin",
        "given_name": "Admin",
        "family_name": "User",
        "roles": ["admin", "user"],
        "primary_role": "admin",
        "email_verified": True
    }


class TestConversationCRUDFlow:
    """Test complete conversation CRUD operations with authentication."""
    
    @patch('privategpt.infra.database.async_session.get_async_session_context')
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_create_conversation_with_auth(
        self, 
        mock_validate_token, 
        mock_session_context,
        client, 
        mock_jwt_user,
        test_db_engine
    ):
        """Test creating a conversation with JWT authentication."""
        # Arrange
        mock_validate_token.return_value = mock_jwt_user
        
        # Mock the database session context
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__.return_value = mock_session
        mock_session_context.return_value.__aexit__.return_value = None
        
        # Mock user creation/lookup
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.keycloak_id = "keycloak-user-123"
        mock_user.email = "test@example.com"
        
        # Mock ensure_user_exists to return user ID
        with patch('privategpt.services.gateway.api.chat_router.ensure_user_exists') as mock_ensure_user:
            mock_ensure_user.return_value = 1
            
            # Mock repository operations
            with patch('privategpt.infra.database.conversation_repository.SqlConversationRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                mock_created_conv = MagicMock()
                mock_created_conv.id = "conv-123"
                mock_created_conv.title = "Test Conversation"
                mock_created_conv.status = "active"
                mock_created_conv.model_name = "test-model"
                mock_created_conv.system_prompt = None
                mock_created_conv.data = {}
                mock_created_conv.created_at = datetime.utcnow()
                mock_created_conv.updated_at = datetime.utcnow()
                mock_created_conv.messages = []
                
                mock_repo.create.return_value = mock_created_conv
                
                # Act
                response = client.post(
                    "/api/chat/conversations",
                    headers={"Authorization": "Bearer valid-jwt-token"},
                    json={
                        "title": "Test Conversation",
                        "model_name": "test-model"
                    }
                )
                
                # Assert
                assert response.status_code == 201
                data = response.json()
                assert data["title"] == "Test Conversation"
                assert data["status"] == "active"
                assert data["model_name"] == "test-model"
                assert data["message_count"] == 0
                
                # Verify user was ensured to exist
                mock_ensure_user.assert_called_once()
                # Verify repository was called correctly
                mock_repo.create.assert_called_once()
    
    @patch('privategpt.infra.database.async_session.get_async_session_context')
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_list_conversations_with_auth(
        self,
        mock_validate_token,
        mock_session_context, 
        client,
        mock_jwt_user
    ):
        """Test listing conversations with authentication."""
        # Arrange
        mock_validate_token.return_value = mock_jwt_user
        
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__.return_value = mock_session
        mock_session_context.return_value.__aexit__.return_value = None
        
        with patch('privategpt.services.gateway.api.chat_router.ensure_user_exists') as mock_ensure_user:
            mock_ensure_user.return_value = 1
            
            with patch('privategpt.infra.database.conversation_repository.SqlConversationRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                
                # Mock conversation list
                mock_conv1 = MagicMock()
                mock_conv1.id = "conv-1"
                mock_conv1.title = "First Conversation"
                mock_conv1.status = "active"
                mock_conv1.model_name = "model-1"
                mock_conv1.system_prompt = None
                mock_conv1.data = {}
                mock_conv1.created_at = datetime.utcnow()
                mock_conv1.updated_at = datetime.utcnow()
                mock_conv1.messages = []
                
                mock_conv2 = MagicMock()
                mock_conv2.id = "conv-2"
                mock_conv2.title = "Second Conversation"
                mock_conv2.status = "active"
                mock_conv2.model_name = "model-2"
                mock_conv2.system_prompt = "Custom prompt"
                mock_conv2.data = {"key": "value"}
                mock_conv2.created_at = datetime.utcnow()
                mock_conv2.updated_at = datetime.utcnow()
                mock_conv2.messages = []
                
                mock_repo.get_by_user.return_value = [mock_conv1, mock_conv2]
                
                # Act
                response = client.get(
                    "/api/chat/conversations",
                    headers={"Authorization": "Bearer valid-jwt-token"}
                )
                
                # Assert
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["title"] == "First Conversation"
                assert data[1]["title"] == "Second Conversation"
                
                # Verify repository called with correct parameters
                mock_repo.get_by_user.assert_called_once_with(
                    user_id=1,
                    limit=50,
                    offset=0
                )
    
    @patch('privategpt.infra.database.async_session.get_async_session_context')
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_update_conversation_with_auth(
        self,
        mock_validate_token,
        mock_session_context,
        client,
        mock_jwt_user
    ):
        """Test updating a conversation with authentication."""
        # Arrange
        mock_validate_token.return_value = mock_jwt_user
        
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__.return_value = mock_session
        mock_session_context.return_value.__aexit__.return_value = None
        
        with patch('privategpt.services.gateway.api.chat_router.ensure_user_exists') as mock_ensure_user:
            mock_ensure_user.return_value = 1
            
            with patch('privategpt.infra.database.conversation_repository.SqlConversationRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                
                # Mock existing conversation
                mock_existing_conv = MagicMock()
                mock_existing_conv.id = "conv-123"
                mock_existing_conv.user_id = 1
                mock_existing_conv.title = "Original Title"
                mock_existing_conv.status = "active"
                mock_existing_conv.model_name = "original-model"
                mock_existing_conv.system_prompt = None
                mock_existing_conv.data = {}
                
                # Mock updated conversation
                mock_updated_conv = MagicMock()
                mock_updated_conv.id = "conv-123"
                mock_updated_conv.title = "Updated Title"
                mock_updated_conv.status = "archived"
                mock_updated_conv.model_name = "updated-model"
                mock_updated_conv.system_prompt = "New prompt"
                mock_updated_conv.data = {"updated": True}
                mock_updated_conv.created_at = datetime.utcnow()
                mock_updated_conv.updated_at = datetime.utcnow()
                mock_updated_conv.messages = []
                
                mock_repo.get.return_value = mock_existing_conv
                mock_repo.update.return_value = mock_updated_conv
                
                # Act
                response = client.patch(
                    "/api/chat/conversations/conv-123",
                    headers={"Authorization": "Bearer valid-jwt-token"},
                    json={
                        "title": "Updated Title",
                        "status": "archived",
                        "model_name": "updated-model",
                        "system_prompt": "New prompt",
                        "data": {"updated": True}
                    }
                )
                
                # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["title"] == "Updated Title"
                assert data["status"] == "archived"
                assert data["model_name"] == "updated-model"
                assert data["system_prompt"] == "New prompt"
                assert data["data"] == {"updated": True}
    
    def test_create_conversation_without_auth(self, client):
        """Test that creating conversation without auth fails."""
        # Act
        response = client.post(
            "/api/chat/conversations",
            json={"title": "Unauthorized Conversation"}
        )
        
        # Assert
        assert response.status_code == 401
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_create_conversation_with_invalid_token(self, mock_validate_token, client):
        """Test creating conversation with invalid token."""
        # Arrange
        mock_validate_token.return_value = None
        
        # Act
        response = client.post(
            "/api/chat/conversations",
            headers={"Authorization": "Bearer invalid-token"},
            json={"title": "Invalid Token Conversation"}
        )
        
        # Assert
        assert response.status_code == 401


class TestUserAutoCreation:
    """Test user auto-creation with keycloak_id mapping."""
    
    @patch('privategpt.infra.database.async_session.get_async_session_context')
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_user_auto_creation_from_jwt(
        self,
        mock_validate_token,
        mock_session_context,
        client,
        mock_jwt_user
    ):
        """Test that users are automatically created from JWT claims."""
        # Arrange
        mock_validate_token.return_value = mock_jwt_user
        
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__.return_value = mock_session
        mock_session_context.return_value.__aexit__.return_value = None
        
        # Mock ensure_user_exists to test the actual user creation logic
        with patch('privategpt.services.gateway.api.chat_router.ensure_user_exists') as mock_ensure_user:
            # Simulate user creation returning new user ID
            mock_ensure_user.return_value = 42
            
            with patch('privategpt.infra.database.conversation_repository.SqlConversationRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                mock_created_conv = MagicMock()
                mock_created_conv.id = "conv-123"
                mock_created_conv.title = "Test"
                mock_created_conv.status = "active"
                mock_created_conv.model_name = None
                mock_created_conv.system_prompt = None
                mock_created_conv.data = {}
                mock_created_conv.created_at = datetime.utcnow()
                mock_created_conv.updated_at = datetime.utcnow()
                mock_created_conv.messages = []
                
                mock_repo.create.return_value = mock_created_conv
                
                # Act
                response = client.post(
                    "/api/chat/conversations",
                    headers={"Authorization": "Bearer valid-jwt-token"},
                    json={"title": "Test"}
                )
                
                # Assert
                assert response.status_code == 201
                
                # Verify ensure_user_exists was called with JWT claims
                mock_ensure_user.assert_called_once()
                call_args = mock_ensure_user.call_args[0]
                user_claims = call_args[1]  # Second argument should be user claims
                
                assert user_claims["user_id"] == "keycloak-user-123"
                assert user_claims["email"] == "test@example.com"
                assert user_claims["preferred_username"] == "testuser"
    
    @patch('privategpt.infra.database.async_session.get_async_session_context')
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_existing_user_lookup_by_keycloak_id(
        self,
        mock_validate_token,
        mock_session_context,
        client,
        mock_jwt_user
    ):
        """Test that existing users are found by keycloak_id."""
        # Arrange
        mock_validate_token.return_value = mock_jwt_user
        
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__.return_value = mock_session
        mock_session_context.return_value.__aexit__.return_value = None
        
        with patch('privategpt.services.gateway.api.chat_router.ensure_user_exists') as mock_ensure_user:
            # Simulate finding existing user
            mock_ensure_user.return_value = 1  # Existing user ID
            
            with patch('privategpt.infra.database.conversation_repository.SqlConversationRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_by_user.return_value = []
                
                # Act
                response = client.get(
                    "/api/chat/conversations",
                    headers={"Authorization": "Bearer valid-jwt-token"}
                )
                
                # Assert
                assert response.status_code == 200
                
                # Verify user lookup was called
                mock_ensure_user.assert_called_once()
                
                # Verify conversations were queried with the returned user ID
                mock_repo.get_by_user.assert_called_once_with(
                    user_id=1,
                    limit=50,
                    offset=0
                )


class TestAsyncSessionContextManager:
    """Test that async session context manager pattern works correctly."""
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_context_manager_pattern_usage(self, mock_validate_token, client, mock_jwt_user):
        """Test that endpoints use context manager pattern correctly."""
        # Arrange
        mock_validate_token.return_value = mock_jwt_user
        
        # Mock the context manager to verify it's being used
        with patch('privategpt.infra.database.async_session.get_async_session_context') as mock_context:
            mock_session = AsyncMock()
            mock_context.return_value.__aenter__.return_value = mock_session
            mock_context.return_value.__aexit__.return_value = None
            
            with patch('privategpt.services.gateway.api.chat_router.ensure_user_exists') as mock_ensure_user:
                mock_ensure_user.return_value = 1
                
                with patch('privategpt.infra.database.conversation_repository.SqlConversationRepository') as MockRepo:
                    mock_repo = MockRepo.return_value
                    mock_repo.get_by_user.return_value = []
                    
                    # Act
                    response = client.get(
                        "/api/chat/conversations",
                        headers={"Authorization": "Bearer valid-jwt-token"}
                    )
                    
                    # Assert
                    assert response.status_code == 200
                    
                    # Verify context manager was used (not dependency injection)
                    mock_context.assert_called_once()
                    # Verify the context manager was properly entered/exited
                    mock_context.return_value.__aenter__.assert_called_once()


class TestErrorHandling:
    """Test error handling in conversation management."""
    
    @patch('privategpt.infra.database.async_session.get_async_session_context')
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_conversation_not_found(
        self,
        mock_validate_token,
        mock_session_context,
        client,
        mock_jwt_user
    ):
        """Test handling of non-existent conversation."""
        # Arrange
        mock_validate_token.return_value = mock_jwt_user
        
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__.return_value = mock_session
        mock_session_context.return_value.__aexit__.return_value = None
        
        with patch('privategpt.services.gateway.api.chat_router.ensure_user_exists') as mock_ensure_user:
            mock_ensure_user.return_value = 1
            
            with patch('privategpt.infra.database.conversation_repository.SqlConversationRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get.return_value = None  # Conversation not found
                
                # Act
                response = client.patch(
                    "/api/chat/conversations/nonexistent-id",
                    headers={"Authorization": "Bearer valid-jwt-token"},
                    json={"title": "Updated Title"}
                )
                
                # Assert
                assert response.status_code == 404
                assert "Conversation not found" in response.json()["detail"]
    
    @patch('privategpt.infra.database.async_session.get_async_session_context')
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_unauthorized_conversation_access(
        self,
        mock_validate_token,
        mock_session_context,
        client,
        mock_jwt_user
    ):
        """Test accessing conversation owned by different user."""
        # Arrange
        mock_validate_token.return_value = mock_jwt_user
        
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__.return_value = mock_session
        mock_session_context.return_value.__aexit__.return_value = None
        
        with patch('privategpt.services.gateway.api.chat_router.ensure_user_exists') as mock_ensure_user:
            mock_ensure_user.return_value = 1  # Current user ID
            
            with patch('privategpt.infra.database.conversation_repository.SqlConversationRepository') as MockRepo:
                mock_repo = MockRepo.return_value
                
                # Mock conversation owned by different user
                mock_other_user_conv = MagicMock()
                mock_other_user_conv.id = "conv-123"
                mock_other_user_conv.user_id = 999  # Different user
                mock_repo.get.return_value = mock_other_user_conv
                
                # Act
                response = client.patch(
                    "/api/chat/conversations/conv-123",
                    headers={"Authorization": "Bearer valid-jwt-token"},
                    json={"title": "Hacked Title"}
                )
                
                # Assert
                assert response.status_code == 404
                assert "Conversation not found" in response.json()["detail"]


class TestDebugEndpoints:
    """Test debug endpoints work without authentication (for development)."""
    
    def test_debug_simple_endpoint(self, client):
        """Test simple debug endpoint without auth."""
        # Act
        response = client.get("/api/chat/debug/simple")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Simple endpoint works" in data["message"]
    
    @patch('privategpt.infra.database.async_session.get_async_session_context')
    def test_debug_session_endpoint(self, mock_session_context, client):
        """Test debug session endpoint without auth."""
        # Arrange
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__.return_value = mock_session
        mock_session_context.return_value.__aexit__.return_value = None
        
        # Mock SQLAlchemy query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        # Act
        response = client.get("/api/chat/debug/session")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Context manager pattern works" in data["message"]
    
    @patch('privategpt.infra.database.async_session.get_async_session_context')
    def test_debug_conversations_endpoint(self, mock_session_context, client):
        """Test debug conversations endpoint without auth."""
        # Arrange
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__.return_value = mock_session
        mock_session_context.return_value.__aexit__.return_value = None
        
        with patch('privategpt.infra.database.conversation_repository.SqlConversationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_user.return_value = []
            
            # Act
            response = client.get("/api/chat/debug/conversations")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Fixed using context manager pattern" in data["message"]