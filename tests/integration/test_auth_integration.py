"""
Integration tests for authentication system.

Tests the complete authentication flow including gateway service,
middleware, route protection, and real service interactions.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from privategpt.services.gateway.api.auth_router import router as auth_router
from privategpt.shared.auth_middleware import KeycloakAuthMiddleware


@pytest.fixture
def gateway_app():
    """Create a test gateway app with authentication middleware."""
    app = FastAPI(title="Test Gateway")
    
    # Add authentication middleware
    app.add_middleware(
        KeycloakAuthMiddleware,
        protected_paths=["/api/"],
        excluded_paths=[
            "/health",
            "/docs",
            "/openapi.json",
            "/api/auth/login",
            "/api/auth/verify",
            "/api/auth/keycloak/config"
        ]
    )
    
    # Include auth router
    app.include_router(auth_router)
    
    # Add test routes
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    @app.get("/api/protected")
    async def protected():
        return {"message": "This is a protected route"}
    
    @app.get("/api/chat/conversations")
    async def chat_conversations():
        return {"conversations": []}
    
    @app.get("/public")
    async def public():
        return {"message": "This is public"}
    
    return app


@pytest.fixture
def client(gateway_app):
    """Test client for the gateway app."""
    return TestClient(gateway_app)


@pytest.fixture
def mock_keycloak_service():
    """Mock Keycloak service for authentication tests."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_user_service():
    """Mock user service for authentication tests."""
    service = AsyncMock()
    return service


@pytest.fixture
def valid_token_response():
    """Sample valid token response from Keycloak."""
    return {
        "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwiZW1haWwiOiJhZG1pbkBhZG1pbi5jb20iLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJhZG1pbkBhZG1pbi5jb20iLCJnaXZlbl9uYW1lIjoiQWRtaW4iLCJmYW1pbHlfbmFtZSI6IlVzZXIiLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsiYWRtaW4iLCJ1c2VyIl19LCJleHAiOjE2NzAyNjg0MDB9.signature",
        "token_type": "bearer",
        "expires_in": 3600,
        "refresh_token": "refresh_token_here",
        "user": {
            "user_id": 1,
            "email": "admin@admin.com",
            "username": "admin@admin.com",
            "first_name": "Admin",
            "last_name": "User",
            "role": "admin"
        }
    }


@pytest.fixture
def valid_user_claims():
    """Sample valid user claims for token validation."""
    return {
        'user_id': 'user123',
        'username': 'admin@admin.com',
        'email': 'admin@admin.com',
        'first_name': 'Admin',
        'last_name': 'User',
        'roles': ['admin', 'user'],
        'primary_role': 'admin',
        'email_verified': True,
        'token_issued_at': 1670264800,
        'token_expires_at': 1670268400,
    }


class TestAuthenticationFlow:
    """Test complete authentication flow."""
    
    @patch('privategpt.services.gateway.api.auth_router.get_keycloak_service')
    @patch('privategpt.services.gateway.api.auth_router.get_user_service')
    def test_login_and_access_protected_route(
        self, 
        mock_get_user_service, 
        mock_get_keycloak_service,
        client,
        mock_keycloak_service,
        mock_user_service,
        valid_token_response
    ):
        """Test complete flow: login -> get token -> access protected route."""
        # Arrange - Setup mocks
        mock_get_keycloak_service.return_value = mock_keycloak_service
        mock_get_user_service.return_value = mock_user_service
        
        # Mock login response
        mock_keycloak_service.login_with_password.return_value = {
            "access_token": valid_token_response["access_token"],
            "expires_in": 3600,
            "refresh_token": "refresh_token"
        }
        
        # Mock user info
        mock_keycloak_service.get_user_info.return_value = {
            "sub": "user123",
            "email": "admin@admin.com",
            "preferred_username": "admin@admin.com",
            "given_name": "Admin",
            "family_name": "User",
            "realm_access": {"roles": ["admin", "user"]}
        }
        
        # Mock user service
        mock_local_user = MagicMock()
        mock_local_user.id = 1
        mock_local_user.email = "admin@admin.com"
        mock_local_user.username = "admin@admin.com"
        mock_local_user.first_name = "Admin"
        mock_local_user.last_name = "User"
        mock_local_user.role = "admin"
        mock_user_service.get_or_create_user_from_keycloak.return_value = mock_local_user
        
        # Step 1: Login
        login_response = client.post(
            "/api/auth/login",
            json={"email": "admin@admin.com", "password": "admin"}
        )
        
        assert login_response.status_code == 200
        token_data = login_response.json()
        access_token = token_data["access_token"]
        
        # Step 2: Mock token validation for protected route access
        with patch('privategpt.shared.auth_middleware.validate_bearer_token') as mock_validate:
            mock_validate.return_value = {
                'user_id': 'user123',
                'username': 'admin@admin.com',
                'email': 'admin@admin.com',
                'roles': ['admin', 'user'],
                'primary_role': 'admin'
            }
            
            # Step 3: Access protected route
            protected_response = client.get(
                "/api/protected",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert protected_response.status_code == 200
            assert protected_response.json()["message"] == "This is a protected route"
    
    def test_access_protected_route_without_token(self, client):
        """Test accessing protected route without authentication token."""
        # Act
        response = client.get("/api/protected")
        
        # Assert
        assert response.status_code == 401
        assert "Invalid or missing authentication token" in response.json()["detail"]
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_access_protected_route_with_invalid_token(self, mock_validate, client):
        """Test accessing protected route with invalid token."""
        # Arrange
        mock_validate.return_value = None
        
        # Act
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        # Assert
        assert response.status_code == 401
        mock_validate.assert_called_once_with("Bearer invalid_token")
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_access_multiple_protected_routes(self, mock_validate, client, valid_user_claims):
        """Test accessing multiple protected routes with valid token."""
        # Arrange
        mock_validate.return_value = valid_user_claims
        
        # Act & Assert
        routes_to_test = [
            "/api/protected",
            "/api/chat/conversations"
        ]
        
        for route in routes_to_test:
            response = client.get(
                route,
                headers={"Authorization": "Bearer valid_token"}
            )
            assert response.status_code == 200, f"Route {route} should be accessible"


class TestRouteProtection:
    """Test route protection configuration."""
    
    def test_public_routes_accessible(self, client):
        """Test that public routes are accessible without authentication."""
        # Test various public routes
        public_routes = [
            "/health",
            "/public",
            "/docs",
            "/openapi.json"
        ]
        
        for route in public_routes:
            response = client.get(route)
            # Should not return 401 (some might return 404 if route doesn't exist)
            assert response.status_code != 401, f"Route {route} should not require auth"
    
    def test_auth_endpoints_accessible(self, client):
        """Test that authentication endpoints are accessible without token."""
        # These should be accessible for login flow
        auth_routes = [
            ("/api/auth/keycloak/config", "GET"),
            ("/api/auth/login", "POST"),
            ("/api/auth/verify", "POST")
        ]
        
        for route, method in auth_routes:
            if method == "GET":
                response = client.get(route)
            else:
                response = client.post(route, json={})
            
            # Should not return 401 (might return 422 for validation errors)
            assert response.status_code != 401, f"Route {route} should not require auth"
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_protected_routes_require_auth(self, mock_validate, client):
        """Test that protected routes require authentication."""
        # Arrange
        mock_validate.return_value = None
        
        # Test protected routes
        protected_routes = [
            "/api/protected",
            "/api/chat/conversations",
            "/api/llm/models"
        ]
        
        for route in protected_routes:
            response = client.get(route)
            assert response.status_code == 401, f"Route {route} should require auth"


class TestTokenValidation:
    """Test token validation scenarios."""
    
    @patch('privategpt.services.gateway.api.auth_router.get_keycloak_service')
    def test_token_verification_endpoint(self, mock_get_keycloak_service, client, mock_keycloak_service):
        """Test the token verification endpoint."""
        # Arrange
        mock_get_keycloak_service.return_value = mock_keycloak_service
        mock_keycloak_service.verify_token.return_value = True
        mock_keycloak_service.get_user_info.return_value = {
            "sub": "user123",
            "email": "admin@admin.com"
        }
        
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
    
    @patch('privategpt.services.gateway.api.auth_router.get_keycloak_service')
    def test_token_verification_invalid_token(self, mock_get_keycloak_service, client, mock_keycloak_service):
        """Test token verification with invalid token."""
        # Arrange
        mock_get_keycloak_service.return_value = mock_keycloak_service
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


class TestErrorScenarios:
    """Test various error scenarios in authentication."""
    
    @patch('privategpt.services.gateway.api.auth_router.get_keycloak_service')
    def test_login_with_service_unavailable(self, mock_get_keycloak_service, client, mock_keycloak_service):
        """Test login when Keycloak service is unavailable."""
        # Arrange
        mock_get_keycloak_service.return_value = mock_keycloak_service
        mock_keycloak_service.login_with_password.side_effect = Exception("Service unavailable")
        
        # Act
        response = client.post(
            "/api/auth/login",
            json={"email": "admin@admin.com", "password": "admin"}
        )
        
        # Assert
        assert response.status_code == 500
        assert "Authentication service unavailable" in response.json()["detail"]
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_middleware_with_token_validation_error(self, mock_validate, client):
        """Test middleware behavior when token validation throws an exception."""
        # Arrange
        mock_validate.side_effect = Exception("Token validation error")
        
        # Act
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer problematic_token"}
        )
        
        # Assert
        # Middleware should handle exceptions gracefully and return 401
        assert response.status_code == 401


class TestConcurrentRequests:
    """Test authentication with concurrent requests."""
    
    @patch('privategpt.shared.auth_middleware.validate_bearer_token')
    def test_multiple_concurrent_requests(self, mock_validate, client, valid_user_claims):
        """Test multiple concurrent requests with the same token."""
        # Arrange
        mock_validate.return_value = valid_user_claims
        
        # Act - Simulate concurrent requests
        responses = []
        for i in range(5):
            response = client.get(
                "/api/protected",
                headers={"Authorization": "Bearer concurrent_token"}
            )
            responses.append(response)
        
        # Assert
        for response in responses:
            assert response.status_code == 200
            assert response.json()["message"] == "This is a protected route"
        
        # Token validation should be called for each request
        assert mock_validate.call_count == 5


class TestTokenExpiration:
    """Test token expiration scenarios."""
    
    @patch('privategpt.services.gateway.api.auth_router.get_keycloak_service')
    def test_refresh_token_flow(self, mock_get_keycloak_service, client, mock_keycloak_service):
        """Test token refresh functionality."""
        # Arrange
        mock_get_keycloak_service.return_value = mock_keycloak_service
        mock_keycloak_service.refresh_token.return_value = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "refresh_token": "new_refresh_token"
        }
        
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
    
    @patch('privategpt.services.gateway.api.auth_router.get_keycloak_service')
    def test_refresh_token_invalid(self, mock_get_keycloak_service, client, mock_keycloak_service):
        """Test refresh with invalid refresh token."""
        # Arrange
        mock_get_keycloak_service.return_value = mock_keycloak_service
        mock_keycloak_service.refresh_token.return_value = None
        
        # Act
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"}
        )
        
        # Assert
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]


class TestLogoutFlow:
    """Test logout functionality."""
    
    @patch('privategpt.services.gateway.api.auth_router.get_keycloak_service')
    def test_logout_success(self, mock_get_keycloak_service, client, mock_keycloak_service):
        """Test successful logout."""
        # Arrange
        mock_get_keycloak_service.return_value = mock_keycloak_service
        mock_keycloak_service.logout.return_value = None
        
        # Act
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Logout successful"
        mock_keycloak_service.logout.assert_called_once_with("valid_token")
    
    def test_logout_without_token(self, client):
        """Test logout without providing token."""
        # Act
        response = client.post("/api/auth/logout")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Logout successful"


class TestKeycloakConfiguration:
    """Test Keycloak configuration endpoint."""
    
    @patch('privategpt.services.gateway.api.auth_router.settings')
    def test_get_keycloak_config(self, mock_settings, client):
        """Test Keycloak configuration retrieval."""
        # Arrange
        mock_settings.keycloak_url = "http://test-keycloak:8080"
        mock_settings.keycloak_realm = "test-realm"
        mock_settings.keycloak_client_id = "test-client"
        
        # Act
        response = client.get("/api/auth/keycloak/config")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "http://test-keycloak:8080"
        assert data["realm"] == "test-realm"
        assert data["clientId"] == "test-client"