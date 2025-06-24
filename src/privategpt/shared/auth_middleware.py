from __future__ import annotations

"""
FastAPI middleware for Keycloak authentication and authorization.
"""

import logging
from typing import Optional, List, Callable

from fastapi import Request, Response, HTTPException, status, Query
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
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Check if path requires authentication
        if not self._requires_auth(request.url.path):
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
        
        return await call_next(request)
    
    def _requires_auth(self, path: str) -> bool:
        """Check if path requires authentication."""
        logger.info(f"Checking auth requirement for path: {path}")
        logger.info(f"Excluded paths: {self.excluded_paths}")
        
        # Check excluded paths first
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                logger.info(f"Path {path} matches excluded pattern {excluded}, skipping auth")
                return False
            
        # Check if path matches protected patterns
        for protected in self.protected_paths:
            if path.startswith(protected):
                logger.info(f"Path {path} matches protected pattern {protected}, requiring auth")
                return True
        
        logger.info(f"Path {path} doesn't match any patterns, no auth required")
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


async def get_current_user_flexible(
    request: Request,
    token: Optional[str] = None  # Can be provided via query param
) -> dict:
    """
    Flexible authentication dependency that works with streaming endpoints.
    
    Checks authentication in the following order:
    1. User already validated by middleware (in request.state)
    2. Authorization header in the request
    3. Token provided as query parameter (for EventSource compatibility)
    
    Usage:
        @app.post("/stream")
        async def stream_endpoint(
            user: dict = Depends(get_current_user_flexible),
            token: Optional[str] = Query(None)  # For EventSource
        ):
            return StreamingResponse(...)
    """
    # First check if middleware already validated
    user = getattr(request.state, 'user', None)
    if user:
        logger.debug("User found in request state from middleware")
        return user
    
    # Check Authorization header
    authorization = request.headers.get("Authorization")
    if authorization:
        logger.debug("Attempting to validate Authorization header")
        user_claims = await validate_bearer_token(authorization)
        if user_claims:
            logger.info("User authenticated via Authorization header", 
                       extra={"user_id": user_claims.get("sub")})
            return user_claims
    
    # Check query parameter token (for EventSource compatibility)
    if token:
        logger.debug("Attempting to validate query parameter token")
        # Add Bearer prefix if not present
        if not token.startswith("Bearer "):
            token = f"Bearer {token}"
        user_claims = await validate_bearer_token(token)
        if user_claims:
            logger.info("User authenticated via query parameter", 
                       extra={"user_id": user_claims.get("sub")})
            return user_claims
    
    # No valid authentication found
    logger.warning("No valid authentication found for request", 
                  extra={"path": request.url.path})
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


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