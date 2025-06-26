from __future__ import annotations

"""
API Gateway routing for PrivateGPT services.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from privategpt.shared.auth_middleware import get_current_user, get_admin_user
from privategpt.services.gateway.core.proxy import get_proxy, ServiceProxy

logger = logging.getLogger(__name__)

router = APIRouter()


# Health and status endpoints
@router.get("/health")
async def health_check():
    """Gateway health check."""
    return {"status": "healthy", "service": "gateway"}


@router.get("/test/auth-check")
async def test_auth_check(request: Request):
    """Test endpoint to check authentication state."""
    user = getattr(request.state, 'user', None)
    return {
        "has_user": user is not None,
        "user": user,
        "path": request.url.path
    }




@router.get("/health/{service}")
async def service_health_check(
    service: str,
    proxy: ServiceProxy = Depends(get_proxy)
):
    """Check health of a specific backend service."""
    result = await proxy.health_check(service)
    return result


@router.get("/status")
async def gateway_status(
    proxy: ServiceProxy = Depends(get_proxy)
):
    """Get status of all backend services."""
    services = ["rag", "llm"]
    status_results = {}
    
    for service in services:
        status_results[service] = await proxy.health_check(service)
    
    return {
        "gateway": {"status": "healthy"},
        "services": status_results
    }


# Authentication endpoints (temporary bridge to Keycloak)
@router.post("/api/auth/login")
async def login(request: Request):
    """Login endpoint - temporarily bridges to Keycloak."""
    from privategpt.services.gateway.core.keycloak_auth import get_keycloak_auth
    
    body = await request.json()
    email = body.get("email")
    password = body.get("password")
    
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password required"
        )
    
    keycloak_auth = get_keycloak_auth()
    result = await keycloak_auth.login_with_password(email, password)
    
    if result:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.post("/api/auth/verify")
async def verify_token(request: Request):
    """Verify authentication token and return user info."""
    from privategpt.shared.keycloak_client import validate_bearer_token
    
    # Get token from Authorization header
    authorization = request.headers.get("Authorization")
    user_claims = await validate_bearer_token(authorization)
    
    if not user_claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token"
        )
    
    return {"valid": True, "user": user_claims}


@router.get("/api/auth/me")
async def get_user_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile."""
    return {"user": user}


# RAG service endpoints
@router.api_route(
    "/api/rag/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False
)
async def proxy_rag_request(
    path: str,
    request: Request,
    proxy: ServiceProxy = Depends(get_proxy),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Proxy requests to RAG service with authentication."""
    return await proxy.proxy_request("rag", request, f"/rag/{path}")


# LLM service endpoints
@router.api_route(
    "/api/llm/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False
)
async def proxy_llm_request(
    path: str,
    request: Request,
    proxy: ServiceProxy = Depends(get_proxy)
):
    """Proxy requests to LLM service."""
    print(f"PROXY_LLM_REQUEST CALLED - path: {path}")
    logger.error(f"PROXY_LLM_REQUEST CALLED - path: {path}")
    
    return await proxy.proxy_request("llm", request, f"/{path}")


# Admin endpoints
@router.api_route(
    "/api/admin/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False
)
async def proxy_admin_request(
    path: str,
    request: Request,
    proxy: ServiceProxy = Depends(get_proxy),
    user: Dict[str, Any] = Depends(get_admin_user)
):
    """Proxy admin requests with admin role requirement."""
    # Route to appropriate service based on path
    if path.startswith("rag/") or path.startswith("documents/"):
        service = "rag"
        service_path = path[4:] if path.startswith("rag/") else f"admin/{path}"
    elif path.startswith("llm/"):
        service = "llm"
        service_path = path[4:]
    else:
        # Default to RAG service for document-related admin operations
        service = "rag"
        service_path = f"admin/{path}"
    
    return await proxy.proxy_request(service, request, f"/{service_path}")


# Keycloak integration endpoints
@router.get("/api/auth/keycloak/config")
async def get_keycloak_config():
    """Get Keycloak configuration for frontend."""
    from privategpt.shared.settings import settings
    
    keycloak_url = getattr(settings, 'keycloak_url', 'http://localhost:8180')
    
    return {
        "realm": "privategpt",
        "auth-server-url": keycloak_url,
        "resource": "privategpt-ui",
        "public-client": False,
        "confidential-port": 0
    }


# Error handlers moved to main.py