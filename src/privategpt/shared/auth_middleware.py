from __future__ import annotations

"""
FastAPI middleware for Keycloak authentication and authorization.
"""

import logging
from typing import Optional, List, Callable

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from privategpt.shared.keycloak_client import validate_bearer_token

logger = logging.getLogger(__name__)

# Security scheme for OpenAPI documentation
security = HTTPBearer()


class KeycloakAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate Keycloak tokens for protected routes.
    
    Adds user information to request state for downstream handlers.
    """
    
    def __init__(
        self,
        app,
        protected_paths: List[str] | None = None,
        excluded_paths: List[str] | None = None,
        require_roles: List[str] | None = None
    ):
        super().__init__(app)
        self.protected_paths = protected_paths or ["/api/"]
        self.excluded_paths = excluded_paths or ["/health", "/docs", "/openapi.json"]
        self.require_roles = require_roles or []
        logger.info(f"KeycloakAuthMiddleware initialized with protected_paths: {self.protected_paths}, excluded_paths: {self.excluded_paths}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication middleware."""
        logger.info(f"Auth middleware processing path: {request.url.path}")
        
        # Check if path requires authentication
        if not self._requires_auth(request.url.path):
            logger.info(f"Path {request.url.path} does not require auth, passing through")
            return await call_next(request)
        
        # Extract and validate token
        authorization = request.headers.get("Authorization")
        user_claims = await validate_bearer_token(authorization)
        
        if not user_claims:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check role requirements
        if self.require_roles and not self._has_required_role(user_claims, self.require_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Add user info to request state
        request.state.user = user_claims
        
        # Log successful authentication
        logger.info(
            "User authenticated",
            extra={
                "user_id": user_claims.get("user_id"),
                "username": user_claims.get("username"),
                "role": user_claims.get("primary_role"),
                "path": request.url.path
            }
        )
        
        return await call_next(request)
    
    def _requires_auth(self, path: str) -> bool:
        """Check if path requires authentication."""
        # Check excluded paths first
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                logger.info(f"Path {path} excluded from auth (matches {excluded})")
                return False
        
        # Check if path matches protected patterns
        for protected in self.protected_paths:
            if path.startswith(protected):
                logger.info(f"Path {path} requires auth (matches {protected})")
                return True
        
        logger.info(f"Path {path} does not match any auth rules")
        return False
    
    def _has_required_role(self, user_claims: dict, required_roles: List[str]) -> bool:
        """Check if user has any of the required roles."""
        user_roles = user_claims.get("roles", [])
        return any(role in user_roles for role in required_roles)


# Dependency functions for route-level authentication

async def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency to get current authenticated user.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"user": user}
    """
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user


async def get_admin_user(request: Request) -> dict:
    """
    FastAPI dependency to require admin role.
    
    Usage:
        @app.get("/admin")
        async def admin_route(user: dict = Depends(get_admin_user)):
            return {"admin": user}
    """
    user = await get_current_user(request)
    if user.get("primary_role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return user


def require_roles(required_roles: List[str]):
    """
    Create a dependency that requires specific roles.
    
    Usage:
        @app.get("/special")
        async def special_route(user: dict = Depends(require_roles(["admin", "special"]))):
            return {"user": user}
    """
    async def _check_roles(request: Request) -> dict:
        user = await get_current_user(request)
        user_roles = user.get("roles", [])
        
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(required_roles)}"
            )
        return user
    
    return _check_roles


# Helper function to extract token from request
async def get_token_from_request(request: Request) -> Optional[str]:
    """Extract JWT token from request authorization header."""
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None