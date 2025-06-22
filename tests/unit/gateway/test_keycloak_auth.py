"""
Tests for the Keycloak authentication service.

Tests JWT token validation, user info retrieval, and all Keycloak integration
functionality including error handling and edge cases.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
import httpx

from privategpt.services.gateway.core.keycloak_auth import (
    KeycloakAuthService,
    KeycloakAuthError
)


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for Keycloak API calls."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def keycloak_service(mock_http_client):
    """Create KeycloakAuthService instance with mocked HTTP client."""
    service = KeycloakAuthService()
    service._http_client = mock_http_client
    return service


@pytest.fixture
def sample_token_response():
    """Sample token response from Keycloak."""
    return {
        "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
        "expires_in": 3600,
        "refresh_expires_in": 1800,
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "Bearer",
        "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
        "not-before-policy": 0,
        "session_state": "abcd-1234-efgh-5678",
        "scope": "openid email profile"
    }


@pytest.fixture
def sample_user_info():
    """Sample user info response from Keycloak."""
    return {
        "sub": "1df0eee5-e10d-4262-b553-be8704127920",
        "email_verified": True,
        "name": "Admin User",
        "preferred_username": "admin@admin.com",
        "given_name": "Admin",
        "family_name": "User",
        "email": "admin@admin.com",
        "realm_access": {
            "roles": ["default-roles-privategpt", "offline_access", "uma_authorization"]
        },
        "resource_access": {
            "account": {
                "roles": ["manage-account", "manage-account-links", "view-profile"]
            }
        }
    }


class TestPasswordLogin:
    """Test cases for password-based login."""
    
    @pytest.mark.asyncio
    async def test_login_with_password_success(
        self, keycloak_service, mock_http_client, sample_token_response
    ):
        """Test successful login with valid credentials."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_token_response
        mock_response.raise_for_status.return_value = None
        mock_http_client.post.return_value = mock_response
        
        # Act
        result = await keycloak_service.login_with_password(
            "admin@admin.com", "admin"
        )
        
        # Assert
        assert result == sample_token_response
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert "token" in call_args[0][0]
        assert call_args[1]["data"]["username"] == "admin@admin.com"
        assert call_args[1]["data"]["password"] == "admin"
        assert call_args[1]["data"]["grant_type"] == "password"
        assert call_args[1]["data"]["client_id"] == "privategpt-ui"
    
    @pytest.mark.asyncio
    async def test_login_with_password_invalid_credentials(
        self, keycloak_service, mock_http_client
    ):
        """Test login with invalid credentials."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Invalid user credentials"
        }
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Client Error", request=MagicMock(), response=mock_response
        )
        mock_http_client.post.return_value = mock_response
        
        # Act
        result = await keycloak_service.login_with_password(
            "invalid@example.com", "wrongpassword"
        )
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_login_with_password_service_unavailable(
        self, keycloak_service, mock_http_client
    ):
        """Test login when Keycloak service is unavailable."""
        # Arrange
        mock_http_client.post.side_effect = httpx.ConnectError("Connection failed")
        
        # Act & Assert
        with pytest.raises(KeycloakAuthError) as exc_info:
            await keycloak_service.login_with_password("admin@admin.com", "admin")
        
        assert "Connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_login_with_password_malformed_response(
        self, keycloak_service, mock_http_client
    ):
        """Test login with malformed JSON response."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status.return_value = None
        mock_http_client.post.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(KeycloakAuthError) as exc_info:
            await keycloak_service.login_with_password("admin@admin.com", "admin")
        
        assert "Failed to parse response" in str(exc_info.value)


class TestTokenVerification:
    """Test cases for token verification."""
    
    @pytest.mark.asyncio
    async def test_verify_token_valid(self, keycloak_service, mock_http_client):
        """Test verification of valid token."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True}
        mock_response.raise_for_status.return_value = None
        mock_http_client.post.return_value = mock_response
        
        # Act
        result = await keycloak_service.verify_token("valid_token")
        
        # Assert
        assert result is True
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert "introspect" in call_args[0][0]
        assert call_args[1]["data"]["token"] == "valid_token"
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, keycloak_service, mock_http_client):
        """Test verification of invalid token."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": False}
        mock_response.raise_for_status.return_value = None
        mock_http_client.post.return_value = mock_response
        
        # Act
        result = await keycloak_service.verify_token("invalid_token")
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_token_service_error(self, keycloak_service, mock_http_client):
        """Test token verification when service returns error."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error", request=MagicMock(), response=mock_response
        )
        mock_http_client.post.return_value = mock_response
        
        # Act
        result = await keycloak_service.verify_token("some_token")
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_token_connection_error(self, keycloak_service, mock_http_client):
        """Test token verification with connection error."""
        # Arrange
        mock_http_client.post.side_effect = httpx.ConnectError("Connection failed")
        
        # Act
        result = await keycloak_service.verify_token("some_token")
        
        # Assert
        assert result is False


class TestUserInfo:
    """Test cases for user info retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_user_info_success(
        self, keycloak_service, mock_http_client, sample_user_info
    ):
        """Test successful user info retrieval."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_user_info
        mock_response.raise_for_status.return_value = None
        mock_http_client.get.return_value = mock_response
        
        # Act
        result = await keycloak_service.get_user_info("valid_token")
        
        # Assert
        assert result == sample_user_info
        mock_http_client.get.assert_called_once()
        call_args = mock_http_client.get.call_args
        assert "userinfo" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer valid_token"
    
    @pytest.mark.asyncio
    async def test_get_user_info_invalid_token(self, keycloak_service, mock_http_client):
        """Test user info retrieval with invalid token."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=mock_response
        )
        mock_http_client.get.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(KeycloakAuthError) as exc_info:
            await keycloak_service.get_user_info("invalid_token")
        
        assert "Failed to get user info" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_user_info_connection_error(self, keycloak_service, mock_http_client):
        """Test user info retrieval with connection error."""
        # Arrange
        mock_http_client.get.side_effect = httpx.ConnectError("Connection failed")
        
        # Act & Assert
        with pytest.raises(KeycloakAuthError) as exc_info:
            await keycloak_service.get_user_info("some_token")
        
        assert "Connection failed" in str(exc_info.value)


class TestTokenRefresh:
    """Test cases for token refresh."""
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, keycloak_service, mock_http_client, sample_token_response
    ):
        """Test successful token refresh."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_token_response
        mock_response.raise_for_status.return_value = None
        mock_http_client.post.return_value = mock_response
        
        # Act
        result = await keycloak_service.refresh_token("valid_refresh_token")
        
        # Assert
        assert result == sample_token_response
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert "token" in call_args[0][0]
        assert call_args[1]["data"]["refresh_token"] == "valid_refresh_token"
        assert call_args[1]["data"]["grant_type"] == "refresh_token"
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, keycloak_service, mock_http_client):
        """Test refresh with invalid refresh token."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Invalid refresh token"
        }
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=MagicMock(), response=mock_response
        )
        mock_http_client.post.return_value = mock_response
        
        # Act
        result = await keycloak_service.refresh_token("invalid_refresh_token")
        
        # Assert
        assert result is None


class TestLogout:
    """Test cases for logout functionality."""
    
    @pytest.mark.asyncio
    async def test_logout_success(self, keycloak_service, mock_http_client):
        """Test successful logout."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status.return_value = None
        mock_http_client.post.return_value = mock_response
        
        # Act
        await keycloak_service.logout("valid_token")
        
        # Assert
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert "logout" in call_args[0][0]
        assert call_args[1]["data"]["refresh_token"] == "valid_token"
    
    @pytest.mark.asyncio
    async def test_logout_with_invalid_token(self, keycloak_service, mock_http_client):
        """Test logout with invalid token - should not raise exception."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=MagicMock(), response=mock_response
        )
        mock_http_client.post.return_value = mock_response
        
        # Act - should not raise exception
        await keycloak_service.logout("invalid_token")
        
        # Assert
        mock_http_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_logout_connection_error(self, keycloak_service, mock_http_client):
        """Test logout with connection error - should not raise exception."""
        # Arrange
        mock_http_client.post.side_effect = httpx.ConnectError("Connection failed")
        
        # Act - should not raise exception
        await keycloak_service.logout("some_token")
        
        # Assert
        mock_http_client.post.assert_called_once()


class TestServiceConfiguration:
    """Test cases for service configuration and initialization."""
    
    @patch('privategpt.services.gateway.core.keycloak_auth.settings')
    def test_service_initialization(self, mock_settings):
        """Test service initialization with settings."""
        # Arrange
        mock_settings.keycloak_url = "http://test-keycloak:8080"
        mock_settings.keycloak_realm = "test-realm"
        mock_settings.keycloak_client_id = "test-client"
        mock_settings.keycloak_client_secret = "test-secret"
        
        # Act
        service = KeycloakAuthService()
        
        # Assert
        assert service.keycloak_url == "http://test-keycloak:8080"
        assert service.realm == "test-realm"
        assert service.client_id == "test-client"
        assert service.client_secret == "test-secret"
    
    def test_urls_construction(self, keycloak_service):
        """Test URL construction for various endpoints."""
        # Act & Assert
        token_url = keycloak_service._get_token_url()
        userinfo_url = keycloak_service._get_userinfo_url()
        logout_url = keycloak_service._get_logout_url()
        introspect_url = keycloak_service._get_introspect_url()
        
        assert "protocol/openid-connect/token" in token_url
        assert "protocol/openid-connect/userinfo" in userinfo_url
        assert "protocol/openid-connect/logout" in logout_url
        assert "protocol/openid-connect/token/introspect" in introspect_url


class TestErrorHandling:
    """Test cases for error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_http_client_lifecycle(self, keycloak_service):
        """Test HTTP client creation and cleanup."""
        # Act
        await keycloak_service._ensure_http_client()
        
        # Assert
        assert keycloak_service._http_client is not None
        
        # Act - cleanup
        await keycloak_service.close()
        
        # Assert - client should be cleaned up
        assert keycloak_service._http_client is None
    
    @pytest.mark.asyncio
    async def test_multiple_client_creation_calls(self, keycloak_service):
        """Test that multiple calls to _ensure_http_client don't create new clients."""
        # Act
        await keycloak_service._ensure_http_client()
        first_client = keycloak_service._http_client
        
        await keycloak_service._ensure_http_client()
        second_client = keycloak_service._http_client
        
        # Assert
        assert first_client is second_client
    
    def test_keycloak_auth_error_creation(self):
        """Test KeycloakAuthError exception creation."""
        # Act
        error = KeycloakAuthError("Test error message")
        
        # Assert
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


class TestIntegrationScenarios:
    """Test cases for realistic integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_auth_flow(
        self, keycloak_service, mock_http_client, sample_token_response, sample_user_info
    ):
        """Test complete authentication flow: login -> verify -> get user info."""
        # Arrange - Login
        login_response = MagicMock()
        login_response.status_code = 200
        login_response.json.return_value = sample_token_response
        login_response.raise_for_status.return_value = None
        
        # Arrange - Verify
        verify_response = MagicMock()
        verify_response.status_code = 200
        verify_response.json.return_value = {"active": True}
        verify_response.raise_for_status.return_value = None
        
        # Arrange - User Info
        userinfo_response = MagicMock()
        userinfo_response.status_code = 200
        userinfo_response.json.return_value = sample_user_info
        userinfo_response.raise_for_status.return_value = None
        
        mock_http_client.post.side_effect = [login_response, verify_response]
        mock_http_client.get.return_value = userinfo_response
        
        # Act - Complete flow
        login_result = await keycloak_service.login_with_password(
            "admin@admin.com", "admin"
        )
        token = login_result["access_token"]
        
        verify_result = await keycloak_service.verify_token(token)
        user_info = await keycloak_service.get_user_info(token)
        
        # Assert
        assert login_result == sample_token_response
        assert verify_result is True
        assert user_info == sample_user_info
        assert mock_http_client.post.call_count == 2
        assert mock_http_client.get.call_count == 1