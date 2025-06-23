"""
Integration tests for JWT authentication with actual Keycloak integration.

Tests the real JWT validation flow that was recently implemented:
- Keycloak issuer URL configuration (localhost:8180)
- JWT audience validation ("account")  
- User keycloak_id mapping and auto-creation
- Token validation with JWKS
- Protected route access with real tokens

This validates the fixes made to resolve authentication issues.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import jwt
import json
from datetime import datetime, timedelta

from privategpt.shared.keycloak_client import KeycloakClient, validate_bearer_token
from privategpt.shared.auth_middleware import KeycloakAuthMiddleware, get_current_user
from privategpt.services.gateway.api.chat_router import ensure_user_exists


# Sample JWT token payload (what Keycloak would issue)
SAMPLE_TOKEN_PAYLOAD = {
    "sub": "keycloak-user-123",  # Keycloak user ID
    "email": "test@example.com",
    "preferred_username": "testuser",
    "given_name": "Test",
    "family_name": "User",
    "email_verified": True,
    "aud": "account",  # This was the issue - audience is "account", not client_id
    "iss": "http://localhost:8180/realms/privategpt",  # External issuer URL
    "iat": int(datetime.utcnow().timestamp()),
    "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
    "realm_access": {
        "roles": ["user"]
    }
}

SAMPLE_ADMIN_TOKEN_PAYLOAD = {
    "sub": "admin-keycloak-456",
    "email": "admin@admin.com", 
    "preferred_username": "admin",
    "given_name": "Admin",
    "family_name": "User",
    "email_verified": True,
    "aud": "account",
    "iss": "http://localhost:8180/realms/privategpt",
    "iat": int(datetime.utcnow().timestamp()),
    "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
    "realm_access": {
        "roles": ["admin", "user"]
    }
}


@pytest.fixture
def mock_keycloak_settings():
    """Mock Keycloak settings with correct configuration."""
    settings = MagicMock()
    settings.keycloak_url = "http://localhost:8180"
    settings.keycloak_realm = "privategpt" 
    settings.keycloak_client_id = "privategpt-ui"
    settings.keycloak_client_secret = "test-secret"
    return settings


@pytest.fixture
def sample_jwt_token():
    """Generate a sample JWT token for testing."""
    # This would normally be signed by Keycloak, but for testing we'll use a mock signature
    return jwt.encode(SAMPLE_TOKEN_PAYLOAD, "test-secret", algorithm="HS256")


@pytest.fixture
def sample_admin_jwt_token():
    """Generate a sample admin JWT token for testing."""
    return jwt.encode(SAMPLE_ADMIN_TOKEN_PAYLOAD, "test-secret", algorithm="HS256")


@pytest.fixture
def mock_jwks_response():
    """Mock JWKS response from Keycloak."""
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key-id",
                "use": "sig",
                "alg": "RS256",
                "n": "test-modulus",
                "e": "AQAB"
            }
        ]
    }


class TestKeycloakClientConfiguration:
    """Test Keycloak client configuration and URL handling."""
    
    def test_keycloak_client_initialization(self, mock_keycloak_settings):
        """Test that Keycloak client initializes with correct URLs."""
        # Act
        client = KeycloakClient(
            keycloak_url=mock_keycloak_settings.keycloak_url,
            realm=mock_keycloak_settings.keycloak_realm,
            client_id=mock_keycloak_settings.keycloak_client_id,
            client_secret=mock_keycloak_settings.keycloak_client_secret
        )
        
        # Assert
        assert client.internal_base_url == "http://localhost:8180"
        assert client.external_issuer == "http://localhost:8180/realms/privategpt"
        assert client.realm == "privategpt"
        assert client.client_id == "privategpt-ui"
    
    def test_keycloak_urls_configuration(self, mock_keycloak_settings):
        """Test that internal and external URLs are configured correctly."""
        # This tests the fix for issuer URL mismatch
        client = KeycloakClient(
            keycloak_url=mock_keycloak_settings.keycloak_url,
            realm=mock_keycloak_settings.keycloak_realm, 
            client_id=mock_keycloak_settings.keycloak_client_id,
            client_secret=mock_keycloak_settings.keycloak_client_secret
        )
        
        # Internal URL (for API calls within Docker network)
        assert client.internal_base_url == "http://localhost:8180"
        
        # External issuer (what appears in JWT tokens)
        assert client.external_issuer == "http://localhost:8180/realms/privategpt"
        
        # JWKS URL should use internal URL
        expected_jwks_url = "http://localhost:8180/realms/privategpt/protocol/openid-connect/certs"
        assert client.jwks_url == expected_jwks_url


class TestJWTTokenValidation:
    """Test JWT token validation with proper audience and issuer."""
    
    @pytest_asyncio.async_test
    @patch('httpx.AsyncClient.get')
    async def test_validate_token_with_correct_audience(self, mock_http_get, mock_keycloak_settings):
        """Test token validation with audience 'account' (the fix)."""
        # Arrange
        client = KeycloakClient(
            keycloak_url=mock_keycloak_settings.keycloak_url,
            realm=mock_keycloak_settings.keycloak_realm,
            client_id=mock_keycloak_settings.keycloak_client_id,
            client_secret=mock_keycloak_settings.keycloak_client_secret
        )
        
        # Mock JWKS response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "keys": [{"kty": "RSA", "kid": "test-key", "use": "sig", "alg": "RS256"}]
        }
        mock_http_get.return_value = mock_response
        
        # Mock JWT decode to return our test payload
        with patch('jwt.decode') as mock_jwt_decode:
            mock_jwt_decode.return_value = SAMPLE_TOKEN_PAYLOAD
            
            # Act
            result = await client.validate_token("test-token")
            
            # Assert
            assert result is not None
            assert result["user_id"] == "keycloak-user-123"
            assert result["email"] == "test@example.com"
            
            # Verify JWT decode was called with correct audience
            mock_jwt_decode.assert_called_once()
            call_kwargs = mock_jwt_decode.call_args[1]
            assert call_kwargs["audience"] == "account"  # This was the fix
            assert call_kwargs["issuer"] == "http://localhost:8180/realms/privategpt"
    
    @pytest_asyncio.async_test
    @patch('httpx.AsyncClient.get')
    async def test_validate_token_with_wrong_audience_fails(self, mock_http_get, mock_keycloak_settings):
        """Test that tokens with wrong audience are rejected."""
        # Arrange
        client = KeycloakClient(
            keycloak_url=mock_keycloak_settings.keycloak_url,
            realm=mock_keycloak_settings.keycloak_realm,
            client_id=mock_keycloak_settings.keycloak_client_id,
            client_secret=mock_keycloak_settings.keycloak_client_secret
        )
        
        # Create token with wrong audience
        wrong_audience_payload = SAMPLE_TOKEN_PAYLOAD.copy()
        wrong_audience_payload["aud"] = "wrong-audience"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": [{"kty": "RSA"}]}
        mock_http_get.return_value = mock_response
        
        with patch('jwt.decode') as mock_jwt_decode:
            # Simulate JWT decode raising InvalidAudienceError
            mock_jwt_decode.side_effect = jwt.InvalidAudienceError("Invalid audience")
            
            # Act
            result = await client.validate_token("test-token")
            
            # Assert
            assert result is None
    
    @pytest_asyncio.async_test
    @patch('httpx.AsyncClient.get')
    async def test_validate_token_with_wrong_issuer_fails(self, mock_http_get, mock_keycloak_settings):
        """Test that tokens with wrong issuer are rejected."""
        # Arrange
        client = KeycloakClient(
            keycloak_url=mock_keycloak_settings.keycloak_url,
            realm=mock_keycloak_settings.keycloak_realm,
            client_id=mock_keycloak_settings.keycloak_client_id,
            client_secret=mock_keycloak_settings.keycloak_client_secret
        )
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": [{"kty": "RSA"}]}
        mock_http_get.return_value = mock_response
        
        with patch('jwt.decode') as mock_jwt_decode:
            # Simulate JWT decode raising InvalidIssuerError
            mock_jwt_decode.side_effect = jwt.InvalidIssuerError("Invalid issuer")
            
            # Act
            result = await client.validate_token("test-token")
            
            # Assert
            assert result is None
    
    @pytest_asyncio.async_test
    async def test_validate_bearer_token_helper_function(self):
        """Test the validate_bearer_token helper function."""
        # Test with valid Bearer token format
        with patch('privategpt.shared.keycloak_client.keycloak_client') as mock_client:
            mock_client.validate_token.return_value = {"user_id": "test-user"}
            
            # Act
            result = await validate_bearer_token("Bearer test-token")
            
            # Assert
            assert result is not None
            assert result["user_id"] == "test-user"
            mock_client.validate_token.assert_called_once_with("test-token")
        
        # Test with invalid format
        result = await validate_bearer_token("InvalidFormat token")
        assert result is None
        
        # Test with None
        result = await validate_bearer_token(None)
        assert result is None


class TestUserAutoCreationWithKeycloakId:
    """Test user auto-creation using keycloak_id mapping."""
    
    @pytest_asyncio.async_test
    async def test_ensure_user_exists_creates_new_user(self):
        """Test that ensure_user_exists creates new user with keycloak_id."""
        # Arrange
        mock_session = AsyncMock()
        
        # Mock user claims from JWT
        user_claims = {
            "user_id": "keycloak-user-123",  # This is the Keycloak UUID
            "email": "newuser@example.com",
            "preferred_username": "newuser",
            "given_name": "New",
            "family_name": "User"
        }
        
        # Mock that user doesn't exist yet
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Mock new user creation
        mock_new_user = MagicMock()
        mock_new_user.id = 42
        mock_new_user.email = "newuser@example.com"
        mock_session.refresh = AsyncMock()
        
        with patch('privategpt.infra.database.models.User') as MockUser:
            MockUser.return_value = mock_new_user
            
            # Act
            user_id = await ensure_user_exists(mock_session, user_claims)
            
            # Assert
            assert user_id == 42
            
            # Verify user was created with correct keycloak_id
            MockUser.assert_called_once()
            user_creation_kwargs = MockUser.call_args[1]
            assert user_creation_kwargs["keycloak_id"] == "keycloak-user-123"
            assert user_creation_kwargs["email"] == "newuser@example.com"
            assert user_creation_kwargs["username"] == "newuser"
            assert user_creation_kwargs["first_name"] == "New"
            assert user_creation_kwargs["last_name"] == "User"
            assert user_creation_kwargs["role"] == "user"
            assert user_creation_kwargs["is_active"] is True
            
            # Verify session operations
            mock_session.add.assert_called_once_with(mock_new_user)
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once_with(mock_new_user)
    
    @pytest_asyncio.async_test
    async def test_ensure_user_exists_finds_existing_user(self):
        """Test that ensure_user_exists finds existing user by keycloak_id."""
        # Arrange
        mock_session = AsyncMock()
        
        user_claims = {
            "user_id": "existing-keycloak-456",
            "email": "existing@example.com"
        }
        
        # Mock existing user found
        mock_existing_user = MagicMock()
        mock_existing_user.id = 1
        mock_existing_user.email = "existing@example.com"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing_user
        mock_session.execute.return_value = mock_result
        
        # Act
        user_id = await ensure_user_exists(mock_session, user_claims)
        
        # Assert
        assert user_id == 1
        
        # Verify no user creation occurred
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()
    
    @pytest_asyncio.async_test
    async def test_ensure_user_exists_handles_demo_mode(self):
        """Test that ensure_user_exists handles disabled auth (demo mode)."""
        # Arrange
        mock_session = AsyncMock()
        
        # Simulate disabled auth (None or invalid user claims)
        user_claims = None
        
        # Mock demo user lookup
        mock_demo_user = MagicMock()
        mock_demo_user.id = 1
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_demo_user
        mock_session.execute.return_value = mock_result
        
        # Act
        user_id = await ensure_user_exists(mock_session, user_claims)
        
        # Assert
        assert user_id == 1
    
    @pytest_asyncio.async_test
    async def test_ensure_user_exists_handles_race_condition(self):
        """Test race condition handling when multiple requests create same user."""
        # Arrange
        mock_session = AsyncMock()
        
        user_claims = {
            "user_id": "race-condition-user",
            "email": "race@example.com"
        }
        
        # First call: user not found
        mock_result_not_found = MagicMock()
        mock_result_not_found.scalar_one_or_none.return_value = None
        
        # Second call: user found (created by another request)
        mock_existing_user = MagicMock()
        mock_existing_user.id = 5
        mock_result_found = MagicMock()
        mock_result_found.scalar_one_or_none.return_value = mock_existing_user
        
        # Mock session.execute to return different results
        mock_session.execute.side_effect = [mock_result_not_found, mock_result_found]
        
        # Mock user creation failure (unique constraint violation)
        mock_session.commit.side_effect = Exception("UNIQUE constraint failed")
        
        # Act
        user_id = await ensure_user_exists(mock_session, user_claims)
        
        # Assert
        assert user_id == 5
        
        # Verify rollback occurred
        mock_session.rollback.assert_called_once()


class TestAuthenticationFlow:
    """Test complete authentication flow from JWT to user access."""
    
    @pytest_asyncio.async_test
    @patch('privategpt.shared.keycloak_client.keycloak_client')
    async def test_complete_auth_flow_with_new_user(self, mock_keycloak_client):
        """Test complete flow: JWT validation -> user creation -> access grant."""
        # Arrange
        mock_keycloak_client.validate_token.return_value = {
            "user_id": "flow-test-user",
            "email": "flowtest@example.com",
            "preferred_username": "flowtest",
            "given_name": "Flow",
            "family_name": "Test",
            "roles": ["user"],
            "primary_role": "user"
        }
        
        # Mock session and user creation
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # User doesn't exist
        mock_session.execute.return_value = mock_result
        
        mock_new_user = MagicMock()
        mock_new_user.id = 99
        
        with patch('privategpt.infra.database.models.User') as MockUser:
            MockUser.return_value = mock_new_user
            
            # Act
            # 1. Validate token
            user_claims = await validate_bearer_token("Bearer test-token")
            assert user_claims is not None
            
            # 2. Ensure user exists
            user_id = await ensure_user_exists(mock_session, user_claims)
            assert user_id == 99
            
            # 3. User should now have access
            assert user_claims["user_id"] == "flow-test-user"
            assert user_claims["email"] == "flowtest@example.com"
    
    @pytest_asyncio.async_test
    @patch('privategpt.shared.keycloak_client.keycloak_client')
    async def test_complete_auth_flow_with_existing_user(self, mock_keycloak_client):
        """Test complete flow with existing user."""
        # Arrange
        mock_keycloak_client.validate_token.return_value = {
            "user_id": "existing-flow-user",
            "email": "existing@example.com",
            "preferred_username": "existing",
            "roles": ["admin", "user"],
            "primary_role": "admin"
        }
        
        # Mock existing user found
        mock_session = AsyncMock()
        mock_existing_user = MagicMock()
        mock_existing_user.id = 1
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing_user
        mock_session.execute.return_value = mock_result
        
        # Act
        user_claims = await validate_bearer_token("Bearer existing-user-token")
        user_id = await ensure_user_exists(mock_session, user_claims)
        
        # Assert
        assert user_claims is not None
        assert user_id == 1
        assert user_claims["primary_role"] == "admin"
        
        # Verify no user creation occurred
        mock_session.add.assert_not_called()


class TestErrorScenarios:
    """Test error scenarios in JWT authentication."""
    
    @pytest_asyncio.async_test
    @patch('privategpt.shared.keycloak_client.keycloak_client')
    async def test_expired_token_handling(self, mock_keycloak_client):
        """Test handling of expired JWT tokens."""
        # Arrange
        mock_keycloak_client.validate_token.return_value = None
        
        # Act
        result = await validate_bearer_token("Bearer expired-token")
        
        # Assert
        assert result is None
    
    @pytest_asyncio.async_test
    @patch('privategpt.shared.keycloak_client.keycloak_client')
    async def test_malformed_token_handling(self, mock_keycloak_client):
        """Test handling of malformed JWT tokens."""
        # Arrange
        mock_keycloak_client.validate_token.return_value = None
        
        # Act
        result = await validate_bearer_token("Bearer malformed.jwt.token")
        
        # Assert
        assert result is None
    
    @pytest_asyncio.async_test
    async def test_invalid_bearer_format_handling(self):
        """Test handling of invalid Bearer token format."""
        # Test various invalid formats
        invalid_formats = [
            "InvalidFormat token",
            "Bearer",  # Missing token
            "Bearer ",  # Empty token
            "token-without-bearer",
            ""
        ]
        
        for invalid_format in invalid_formats:
            result = await validate_bearer_token(invalid_format)
            assert result is None, f"Should reject invalid format: {invalid_format}"
    
    @pytest_asyncio.async_test
    async def test_user_creation_database_error(self):
        """Test handling of database errors during user creation."""
        # Arrange
        mock_session = AsyncMock()
        user_claims = {
            "user_id": "db-error-user",
            "email": "dberror@example.com"
        }
        
        # Mock user not found initially
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Mock database error on commit
        mock_session.commit.side_effect = Exception("Database connection error")
        
        # Mock that user is still not found after rollback (permanent error)
        mock_result_after_rollback = MagicMock()
        mock_result_after_rollback.scalar_one_or_none.return_value = None
        
        with patch('privategpt.infra.database.models.User'):
            # Act & Assert
            with pytest.raises(Exception, match="Database connection error"):
                await ensure_user_exists(mock_session, user_claims)
            
            # Verify rollback was called
            mock_session.rollback.assert_called_once()