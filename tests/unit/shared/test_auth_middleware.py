"""
Tests for the authentication middleware.

Tests route protection, token validation, user state management,
and role-based access control functionality.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.testclient import TestClient

from privategpt.shared.auth_middleware import (
    KeycloakAuthMiddleware,
    get_current_user,
    get_admin_user,
    require_roles,
    get_token_from_request
)


@pytest.fixture
def test_app():
    """Create test FastAPI app."""
    app = FastAPI()
    
    @app.get("/")
    async def root():
        return {"message": "public"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    @app.get("/api/protected")
    async def protected():
        return {"message": "protected"}
    
    @app.get("/api/user")
    async def user_route(user: dict = Depends(get_current_user)):
        return {"user": user}
    
    @app.get("/api/admin")
    async def admin_route(user: dict = Depends(get_admin_user)):
        return {"admin": user}
    
    @app.get("/api/special")
    async def special_route(user: dict = Depends(require_roles(["admin", "special"]))):
        return {"special": user}
    
    return app


@pytest.fixture
def sample_user_claims():
    """Sample user claims for testing."""
    return {
        'user_id': 'user123',
        'username': 'testuser',
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'roles': ['user'],
        'primary_role': 'user',
        'email_verified': True,
        'token_issued_at': 1234567890,
        'token_expires_at': 1234567890 + 3600,
    }


@pytest.fixture
def sample_admin_claims():
    """Sample admin claims for testing."""
    return {
        'user_id': 'admin123',
        'username': 'admin',
        'email': 'admin@example.com',
        'first_name': 'Admin',
        'last_name': 'User',
        'roles': ['admin', 'user'],
        'primary_role': 'admin',
        'email_verified': True,
        'token_issued_at': 1234567890,
        'token_expires_at': 1234567890 + 3600,
    }


class TestKeycloakAuthMiddleware:
    """Test cases for the KeycloakAuthMiddleware."""
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_public_route_no_auth_required(self, mock_validate, test_app):
        """Test that public routes don't require authentication."""
        # Arrange
        app_with_middleware = FastAPI()
        app_with_middleware.add_middleware(
            KeycloakAuthMiddleware,
            protected_paths=["/api/"],
            excluded_paths=["/health", "/"]
        )
        app_with_middleware.mount("/", test_app)
        client = TestClient(app_with_middleware)
        
        # Act
        response = client.get("/")
        
        # Assert
        assert response.status_code == 200
        assert response.json() == {"message": "public"}
        mock_validate.assert_not_called()
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_health_route_excluded(self, mock_validate, test_app):
        """Test that health routes are excluded from authentication."""
        # Arrange
        app_with_middleware = FastAPI()
        app_with_middleware.add_middleware(
            KeycloakAuthMiddleware,
            protected_paths=["/api/"],
            excluded_paths=["/health"]
        )
        app_with_middleware.mount("/", test_app)
        client = TestClient(app_with_middleware)
        
        # Act
        response = client.get("/health")
        
        # Assert
        assert response.status_code == 200
        mock_validate.assert_not_called()
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_protected_route_no_token(self, mock_validate, test_app):
        """Test protected route access without token."""
        # Arrange
        mock_validate.return_value = None
        app_with_middleware = FastAPI()
        app_with_middleware.add_middleware(
            KeycloakAuthMiddleware,
            protected_paths=["/api/"]
        )
        app_with_middleware.mount("/", test_app)
        client = TestClient(app_with_middleware)
        
        # Act
        response = client.get("/api/protected")
        
        # Assert
        assert response.status_code == 401
        assert "Invalid or missing authentication token" in response.json()["detail"]
        mock_validate.assert_called_once()
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_protected_route_valid_token(self, mock_validate, test_app, sample_user_claims):
        """Test protected route access with valid token."""
        # Arrange
        mock_validate.return_value = sample_user_claims
        app_with_middleware = FastAPI()
        app_with_middleware.add_middleware(
            KeycloakAuthMiddleware,
            protected_paths=["/api/"]
        )
        app_with_middleware.mount("/", test_app)
        client = TestClient(app_with_middleware)
        
        # Act
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json() == {"message": "protected"}
        mock_validate.assert_called_once_with("Bearer valid_token")
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_protected_route_invalid_token(self, mock_validate, test_app):
        """Test protected route access with invalid token."""
        # Arrange
        mock_validate.return_value = None
        app_with_middleware = FastAPI()
        app_with_middleware.add_middleware(
            KeycloakAuthMiddleware,
            protected_paths=["/api/"]
        )
        app_with_middleware.mount("/", test_app)
        client = TestClient(app_with_middleware)
        
        # Act
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        # Assert
        assert response.status_code == 401
        mock_validate.assert_called_once_with("Bearer invalid_token")
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_role_requirement_insufficient_permissions(self, mock_validate, test_app, sample_user_claims):
        """Test route access with insufficient role permissions."""
        # Arrange
        mock_validate.return_value = sample_user_claims
        app_with_middleware = FastAPI()
        app_with_middleware.add_middleware(
            KeycloakAuthMiddleware,
            protected_paths=["/api/"],
            require_roles=["admin"]  # User only has "user" role
        )
        app_with_middleware.mount("/", test_app)
        client = TestClient(app_with_middleware)
        
        # Act
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Assert
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_role_requirement_sufficient_permissions(self, mock_validate, test_app, sample_admin_claims):
        """Test route access with sufficient role permissions."""
        # Arrange
        mock_validate.return_value = sample_admin_claims
        app_with_middleware = FastAPI()
        app_with_middleware.add_middleware(
            KeycloakAuthMiddleware,
            protected_paths=["/api/"],
            require_roles=["admin"]
        )
        app_with_middleware.mount("/", test_app)
        client = TestClient(app_with_middleware)
        
        # Act
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer admin_token"}
        )
        
        # Assert
        assert response.status_code == 200
        mock_validate.assert_called_once()
    
    def test_requires_auth_logic(self):
        """Test the _requires_auth method logic."""
        # Arrange
        middleware = KeycloakAuthMiddleware(
            app=MagicMock(),
            protected_paths=["/api/", "/admin/"],
            excluded_paths=["/health", "/docs", "/api/auth/login"]
        )
        
        # Test excluded paths
        assert not middleware._requires_auth("/health")
        assert not middleware._requires_auth("/docs")
        assert not middleware._requires_auth("/api/auth/login")
        
        # Test protected paths
        assert middleware._requires_auth("/api/users")
        assert middleware._requires_auth("/admin/settings")
        
        # Test unprotected paths
        assert not middleware._requires_auth("/public")
        assert not middleware._requires_auth("/")
    
    def test_has_required_role_logic(self):
        """Test the _has_required_role method logic."""
        # Arrange
        middleware = KeycloakAuthMiddleware(app=MagicMock())
        
        user_claims = {"roles": ["user", "editor"]}
        admin_claims = {"roles": ["admin", "user"]}
        
        # Test role matching
        assert middleware._has_required_role(user_claims, ["user"])
        assert middleware._has_required_role(user_claims, ["editor"])
        assert middleware._has_required_role(user_claims, ["user", "admin"])  # OR logic
        assert not middleware._has_required_role(user_claims, ["admin"])
        
        assert middleware._has_required_role(admin_claims, ["admin"])
        assert middleware._has_required_role(admin_claims, ["admin", "super"])  # OR logic


class TestDependencyFunctions:
    """Test cases for FastAPI dependency functions."""
    
    def test_get_current_user_success(self, sample_user_claims):
        """Test successful user retrieval from request state."""
        # Arrange
        request = MagicMock()
        request.state.user = sample_user_claims
        
        # Act & Assert (should not raise)
        result = pytest_asyncio.run(get_current_user(request))
        assert result == sample_user_claims
    
    def test_get_current_user_no_user_in_state(self):
        """Test user retrieval when no user in request state."""
        # Arrange
        request = MagicMock()
        request.state.user = None
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            pytest_asyncio.run(get_current_user(request))
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in str(exc_info.value.detail)
    
    def test_get_current_user_missing_state(self):
        """Test user retrieval when request has no user state."""
        # Arrange
        request = MagicMock()
        del request.state.user  # Simulate missing attribute
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            pytest_asyncio.run(get_current_user(request))
        
        assert exc_info.value.status_code == 401
    
    @patch('privategpt.shared.auth_middleware.get_current_user')
    def test_get_admin_user_success(self, mock_get_user, sample_admin_claims):
        """Test successful admin user retrieval."""
        # Arrange
        mock_get_user.return_value = sample_admin_claims
        request = MagicMock()
        
        # Act
        result = pytest_asyncio.run(get_admin_user(request))
        
        # Assert
        assert result == sample_admin_claims
        mock_get_user.assert_called_once_with(request)
    
    @patch('privategpt.shared.auth_middleware.get_current_user')
    def test_get_admin_user_not_admin(self, mock_get_user, sample_user_claims):
        """Test admin user retrieval for non-admin user."""
        # Arrange
        mock_get_user.return_value = sample_user_claims
        request = MagicMock()
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            pytest_asyncio.run(get_admin_user(request))
        
        assert exc_info.value.status_code == 403
        assert "Admin role required" in str(exc_info.value.detail)
    
    @patch('privategpt.shared.auth_middleware.get_current_user')
    def test_require_roles_success(self, mock_get_user):
        """Test successful role requirement check."""
        # Arrange
        user_claims = {"roles": ["editor", "user"]}
        mock_get_user.return_value = user_claims
        request = MagicMock()
        
        # Create dependency function
        check_roles = require_roles(["editor", "admin"])
        
        # Act
        result = pytest_asyncio.run(check_roles(request))
        
        # Assert
        assert result == user_claims
        mock_get_user.assert_called_once_with(request)
    
    @patch('privategpt.shared.auth_middleware.get_current_user')
    def test_require_roles_insufficient(self, mock_get_user):
        """Test role requirement check with insufficient roles."""
        # Arrange
        user_claims = {"roles": ["user"]}
        mock_get_user.return_value = user_claims
        request = MagicMock()
        
        # Create dependency function
        check_roles = require_roles(["admin", "editor"])
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            pytest_asyncio.run(check_roles(request))
        
        assert exc_info.value.status_code == 403
        assert "admin, editor" in str(exc_info.value.detail)
    
    @patch('privategpt.shared.auth_middleware.get_current_user')
    def test_require_roles_empty_user_roles(self, mock_get_user):
        """Test role requirement check with user having no roles."""
        # Arrange
        user_claims = {"roles": []}
        mock_get_user.return_value = user_claims
        request = MagicMock()
        
        # Create dependency function
        check_roles = require_roles(["user"])
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            pytest_asyncio.run(check_roles(request))
        
        assert exc_info.value.status_code == 403


class TestTokenExtraction:
    """Test cases for token extraction utilities."""
    
    def test_get_token_from_request_valid_bearer(self):
        """Test token extraction from valid Bearer header."""
        # Arrange
        request = MagicMock()
        request.headers.get.return_value = "Bearer abc123def456"
        
        # Act
        result = pytest_asyncio.run(get_token_from_request(request))
        
        # Assert
        assert result == "abc123def456"
    
    def test_get_token_from_request_no_header(self):
        """Test token extraction when no Authorization header."""
        # Arrange
        request = MagicMock()
        request.headers.get.return_value = None
        
        # Act
        result = pytest_asyncio.run(get_token_from_request(request))
        
        # Assert
        assert result is None
    
    def test_get_token_from_request_invalid_format(self):
        """Test token extraction from invalid header format."""
        # Arrange
        request = MagicMock()
        request.headers.get.return_value = "Basic abc123"
        
        # Act
        result = pytest_asyncio.run(get_token_from_request(request))
        
        # Assert
        assert result is None
    
    def test_get_token_from_request_bearer_no_token(self):
        """Test token extraction from Bearer header without token."""
        # Arrange
        request = MagicMock()
        request.headers.get.return_value = "Bearer "
        
        # Act
        result = pytest_asyncio.run(get_token_from_request(request))
        
        # Assert
        assert result == ""


class TestMiddlewareConfiguration:
    """Test cases for middleware configuration options."""
    
    def test_default_configuration(self):
        """Test middleware with default configuration."""
        # Act
        middleware = KeycloakAuthMiddleware(app=MagicMock())
        
        # Assert
        assert middleware.protected_paths == ["/api/"]
        assert "/health" in middleware.excluded_paths
        assert "/docs" in middleware.excluded_paths
        assert "/openapi.json" in middleware.excluded_paths
        assert middleware.require_roles == []
    
    def test_custom_configuration(self):
        """Test middleware with custom configuration."""
        # Act
        middleware = KeycloakAuthMiddleware(
            app=MagicMock(),
            protected_paths=["/api/", "/admin/"],
            excluded_paths=["/health", "/metrics"],
            require_roles=["admin"]
        )
        
        # Assert
        assert middleware.protected_paths == ["/api/", "/admin/"]
        assert middleware.excluded_paths == ["/health", "/metrics"]
        assert middleware.require_roles == ["admin"]
    
    def test_empty_configuration(self):
        """Test middleware with empty configuration."""
        # Act
        middleware = KeycloakAuthMiddleware(
            app=MagicMock(),
            protected_paths=[],
            excluded_paths=[],
            require_roles=[]
        )
        
        # Assert
        assert middleware.protected_paths == []
        assert middleware.excluded_paths == []
        assert middleware.require_roles == []


class TestIntegrationScenarios:
    """Integration test scenarios for realistic use cases."""
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_complete_authentication_flow(self, mock_validate, sample_user_claims):
        """Test complete authentication flow through middleware and dependencies."""
        # Arrange
        mock_validate.return_value = sample_user_claims
        
        app = FastAPI()
        app.add_middleware(
            KeycloakAuthMiddleware,
            protected_paths=["/api/"]
        )
        
        @app.get("/api/user-info")
        async def get_user_info(user: dict = Depends(get_current_user)):
            return {"user_id": user["user_id"], "email": user["email"]}
        
        client = TestClient(app)
        
        # Act
        response = client.get(
            "/api/user-info",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user123"
        assert data["email"] == "test@example.com"
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_admin_route_access_control(self, mock_validate, sample_user_claims, sample_admin_claims):
        """Test admin route access control with different user types."""
        # Arrange
        app = FastAPI()
        app.add_middleware(
            KeycloakAuthMiddleware,
            protected_paths=["/api/"]
        )
        
        @app.get("/api/admin-only")
        async def admin_only(user: dict = Depends(get_admin_user)):
            return {"message": "admin access granted"}
        
        client = TestClient(app)
        
        # Test 1: Regular user should be denied
        mock_validate.return_value = sample_user_claims
        response = client.get(
            "/api/admin-only",
            headers={"Authorization": "Bearer user_token"}
        )
        assert response.status_code == 403
        
        # Test 2: Admin user should be allowed
        mock_validate.return_value = sample_admin_claims
        response = client.get(
            "/api/admin-only",
            headers={"Authorization": "Bearer admin_token"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "admin access granted"
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_multiple_protected_paths(self, mock_validate, sample_user_claims):
        """Test middleware with multiple protected path patterns."""
        # Arrange
        mock_validate.return_value = sample_user_claims
        
        app = FastAPI()
        app.add_middleware(
            KeycloakAuthMiddleware,
            protected_paths=["/api/", "/admin/", "/private/"],
            excluded_paths=["/api/public", "/health"]
        )
        
        @app.get("/api/protected")
        async def api_protected():
            return {"message": "api protected"}
        
        @app.get("/admin/settings")
        async def admin_settings():
            return {"message": "admin settings"}
        
        @app.get("/api/public")
        async def api_public():
            return {"message": "api public"}
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        @app.get("/completely-public")
        async def completely_public():
            return {"message": "completely public"}
        
        client = TestClient(app)
        
        # Test protected paths require auth
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code == 200
        
        response = client.get(
            "/admin/settings",
            headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code == 200
        
        # Test excluded paths don't require auth
        response = client.get("/api/public")
        assert response.status_code == 200
        
        response = client.get("/health")
        assert response.status_code == 200
        
        # Test non-protected paths don't require auth
        response = client.get("/completely-public")
        assert response.status_code == 200