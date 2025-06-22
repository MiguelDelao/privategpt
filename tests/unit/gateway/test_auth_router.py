"""
Tests for the authentication router endpoints.

Tests all authentication endpoints including login, logout, token verification,
and token refresh functionality with both successful and error scenarios.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from privategpt.services.gateway.api.auth_router import (
    router,
    LoginRequest,
    LoginResponse,
    TokenVerifyResponse,
    RefreshTokenRequest,
    get_keycloak_service,
    get_user_service
)
from privategpt.services.gateway.core.keycloak_auth import KeycloakAuthService
from privategpt.services.gateway.core.user_service import UserService


@pytest.fixture
def mock_keycloak_service():
    """Mock Keycloak authentication service."""
    service = AsyncMock(spec=KeycloakAuthService)
    return service


@pytest.fixture
def mock_user_service():
    """Mock user service."""
    service = AsyncMock(spec=UserService)
    return service


@pytest.fixture
def test_app(mock_keycloak_service, mock_user_service):
    """Create test FastAPI app with mocked dependencies."""
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    
    # Override dependencies
    app.dependency_overrides[get_keycloak_service] = lambda: mock_keycloak_service
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    
    return app


@pytest.fixture
def client(test_app):
    """Test client for API calls."""
    return TestClient(test_app)


class TestLogin:
    """Test cases for the login endpoint."""
    
    def test_login_success(self, client, mock_keycloak_service, mock_user_service):
        """Test successful login with valid credentials."""
        # Arrange
        mock_token_response = {
            "access_token": "mock_jwt_token",
            "expires_in": 3600,
            "refresh_token": "mock_refresh_token"
        }
        mock_user_info = {
            "sub": "user123",
            "email": "admin@admin.com",
            "preferred_username": "admin@admin.com",
            "given_name": "Admin",
            "family_name": "User",
            "realm_access": {"roles": ["admin"]}
        }
        
        # Mock Keycloak responses
        mock_keycloak_service.login_with_password.return_value = mock_token_response
        mock_keycloak_service.get_user_info.return_value = mock_user_info
        
        # Mock user service
        mock_local_user = MagicMock()
        mock_local_user.id = 1
        mock_local_user.email = "admin@admin.com"
        mock_local_user.username = "admin@admin.com"
        mock_local_user.first_name = "Admin"
        mock_local_user.last_name = "User"
        mock_local_user.role = "admin"
        
        mock_user_service.get_or_create_user_from_keycloak.return_value = mock_local_user
        
        # Act
        response = client.post(
            "/api/auth/login",
            json={"email": "admin@admin.com", "password": "admin"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "mock_jwt_token"
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
        assert data["refresh_token"] == "mock_refresh_token"
        assert data["user"]["email"] == "admin@admin.com"
        assert data["user"]["role"] == "admin"
        
        # Verify service calls
        mock_keycloak_service.login_with_password.assert_called_once_with(
            "admin@admin.com", "admin"
        )
        mock_user_service.record_user_login.assert_called_once_with(1)
    
    def test_login_invalid_credentials(self, client, mock_keycloak_service):
        """Test login with invalid credentials."""
        # Arrange
        mock_keycloak_service.login_with_password.return_value = None
        
        # Act
        response = client.post(
            "/api/auth/login",
            json={"email": "invalid@example.com", "password": "wrong"}
        )
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "Invalid email or password" in data["detail"]
    
    def test_login_keycloak_service_error(self, client, mock_keycloak_service):
        """Test login when Keycloak service throws an exception."""
        # Arrange
        mock_keycloak_service.login_with_password.side_effect = Exception("Keycloak down")
        
        # Act
        response = client.post(
            "/api/auth/login",
            json={"email": "admin@admin.com", "password": "admin"}
        )
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "Authentication service unavailable" in data["detail"]
    
    def test_login_user_info_processing_error(self, client, mock_keycloak_service, mock_user_service):
        """Test login when user info processing fails but token is valid."""
        # Arrange
        mock_token_response = {
            "access_token": "mock_jwt_token",
            "expires_in": 3600,
            "refresh_token": "mock_refresh_token"
        }
        mock_keycloak_service.login_with_password.return_value = mock_token_response
        mock_keycloak_service.get_user_info.side_effect = Exception("User info error")
        
        # Act
        response = client.post(
            "/api/auth/login",
            json={"email": "admin@admin.com", "password": "admin"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "mock_jwt_token"
        assert "user" not in data or data["user"] is None
    
    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format."""
        # Act
        response = client.post(
            "/api/auth/login",
            json={"email": "invalid-email", "password": "admin"}
        )
        
        # Assert
        assert response.status_code == 422  # Pydantic validation error


class TestTokenVerification:
    """Test cases for the token verification endpoint."""
    
    def test_verify_token_success(self, client, mock_keycloak_service):
        """Test successful token verification."""
        # Arrange
        mock_user_info = {
            "sub": "user123",
            "email": "admin@admin.com",
            "exp": 1234567890
        }
        mock_keycloak_service.verify_token.return_value = True
        mock_keycloak_service.get_user_info.return_value = mock_user_info
        
        # Act
        response = client.post(
            "/api/auth/verify",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user"]["email"] == "admin@admin.com"
    
    def test_verify_token_invalid(self, client, mock_keycloak_service):
        """Test verification of invalid token."""
        # Arrange
        mock_keycloak_service.verify_token.return_value = False
        
        # Act
        response = client.post(
            "/api/auth/verify",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
    
    def test_verify_token_missing_bearer(self, client):
        """Test token verification without Bearer prefix."""
        # Act
        response = client.post(
            "/api/auth/verify",
            headers={"Authorization": "invalid_format"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
    
    def test_verify_token_missing_header(self, client):
        """Test token verification without Authorization header."""
        # Act
        response = client.post("/api/auth/verify")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
    
    def test_verify_token_service_error(self, client, mock_keycloak_service):
        """Test token verification when service throws an exception."""
        # Arrange
        mock_keycloak_service.verify_token.side_effect = Exception("Service error")
        
        # Act
        response = client.post(
            "/api/auth/verify",
            headers={"Authorization": "Bearer some_token"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False


class TestTokenRefresh:
    """Test cases for the token refresh endpoint."""
    
    def test_refresh_token_success(self, client, mock_keycloak_service):
        """Test successful token refresh."""
        # Arrange
        mock_token_response = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "refresh_token": "new_refresh_token"
        }
        mock_keycloak_service.refresh_token.return_value = mock_token_response
        
        # Act
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "valid_refresh_token"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new_access_token"
        assert data["expires_in"] == 3600
        assert data["refresh_token"] == "new_refresh_token"
    
    def test_refresh_token_invalid(self, client, mock_keycloak_service):
        """Test refresh with invalid refresh token."""
        # Arrange
        mock_keycloak_service.refresh_token.return_value = None
        
        # Act
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"}
        )
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "Invalid refresh token" in data["detail"]
    
    def test_refresh_token_service_error(self, client, mock_keycloak_service):
        """Test refresh when service throws an exception."""
        # Arrange
        mock_keycloak_service.refresh_token.side_effect = Exception("Service error")
        
        # Act
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "some_token"}
        )
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "Token refresh failed" in data["detail"]


class TestLogout:
    """Test cases for the logout endpoint."""
    
    def test_logout_success(self, client, mock_keycloak_service):
        """Test successful logout."""
        # Arrange
        mock_keycloak_service.logout.return_value = None
        
        # Act
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logout successful"
        mock_keycloak_service.logout.assert_called_once_with("valid_token")
    
    def test_logout_without_token(self, client):
        """Test logout without Authorization header."""
        # Act
        response = client.post("/api/auth/logout")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logout successful"
    
    def test_logout_keycloak_error(self, client, mock_keycloak_service):
        """Test logout when Keycloak service throws an exception."""
        # Arrange
        mock_keycloak_service.logout.side_effect = Exception("Logout error")
        
        # Act
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer some_token"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logout successful"


class TestKeycloakConfig:
    """Test cases for Keycloak configuration endpoint."""
    
    @patch('privategpt.services.gateway.api.auth_router.settings')
    def test_get_keycloak_config(self, mock_settings, client):
        """Test retrieval of Keycloak configuration."""
        # Arrange
        mock_settings.keycloak_url = "http://keycloak:8080"
        mock_settings.keycloak_realm = "privategpt"
        mock_settings.keycloak_client_id = "privategpt-ui"
        
        # Act
        response = client.get("/api/auth/keycloak/config")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "http://keycloak:8080"
        assert data["realm"] == "privategpt"
        assert data["clientId"] == "privategpt-ui"


class TestRequestModels:
    """Test cases for request/response model validation."""
    
    def test_login_request_validation(self):
        """Test LoginRequest model validation."""
        # Valid request
        request = LoginRequest(email="test@example.com", password="password")
        assert request.email == "test@example.com"
        assert request.password == "password"
        
        # Invalid email should raise validation error
        with pytest.raises(ValueError):
            LoginRequest(email="invalid-email", password="password")
    
    def test_login_response_creation(self):
        """Test LoginResponse model creation."""
        response = LoginResponse(
            access_token="token",
            expires_in=3600,
            refresh_token="refresh",
            user={"id": 1, "email": "test@example.com"}
        )
        assert response.access_token == "token"
        assert response.token_type == "bearer"
        assert response.expires_in == 3600
    
    def test_token_verify_response_creation(self):
        """Test TokenVerifyResponse model creation."""
        response = TokenVerifyResponse(
            valid=True,
            user={"sub": "123", "email": "test@example.com"},
            expires_at="2024-01-01T00:00:00Z"
        )
        assert response.valid is True
        assert response.user["email"] == "test@example.com"
    
    def test_refresh_token_request_validation(self):
        """Test RefreshTokenRequest model validation."""
        request = RefreshTokenRequest(refresh_token="valid_token")
        assert request.refresh_token == "valid_token"