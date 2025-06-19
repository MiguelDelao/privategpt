from __future__ import annotations

"""
PrivateGPT API Gateway Service.

Central entry point for all API requests, providing authentication,
routing, and middleware services.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from privategpt.infra.http.log_middleware import RequestLogMiddleware
from privategpt.shared.auth_middleware import KeycloakAuthMiddleware
from privategpt.services.gateway.api.gateway_router import router as gateway_router
from privategpt.services.gateway.api.user_router import router as user_router
from privategpt.services.gateway.core.proxy import get_proxy
from privategpt.infra.database.models import Base
from privategpt.infra.database.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting API Gateway")
    
    # Initialize database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Startup
    proxy = get_proxy()
    
    try:
        yield
    finally:
        # Shutdown
        logger.info("Shutting down API Gateway")
        await proxy.close()


# Create FastAPI app
app = FastAPI(
    title="PrivateGPT API Gateway",
    description="Central API gateway for PrivateGPT services",
    version="2.0.0",
    lifespan=lifespan
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*"]  # Configure based on deployment
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Streamlit UI
        "http://localhost:3000",  # Future React UI
        "http://localhost",       # General localhost
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Authentication middleware for API routes
app.add_middleware(
    KeycloakAuthMiddleware,
    protected_paths=["/api/"],
    excluded_paths=[
        "/health",
        "/docs", 
        "/openapi.json",
        "/api/auth/keycloak/config",
        "/api/auth/login",  # Login endpoint doesn't need auth
        "/api/auth/verify",  # Let the route handle auth
        "/api/users"  # User endpoints handle their own auth
    ]
)

# Request logging middleware
app.add_middleware(RequestLogMiddleware)

# Include routers
app.include_router(gateway_router)
app.include_router(user_router)

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging."""
    logger.warning(
        "HTTP exception in gateway",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# Root endpoint
@app.get("/")
async def root():
    """API Gateway root endpoint."""
    return {
        "service": "privategpt-api-gateway",
        "version": "2.0.0",
        "status": "healthy"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )