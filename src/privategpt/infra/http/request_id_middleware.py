"""
Request ID middleware for tracking requests across the system.
"""
import uuid
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request IDs to all requests.
    
    Checks for existing X-Request-ID header, generates one if missing.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request state and response headers."""
        # Check for existing request ID or generate new one
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store in request state for easy access
        request.state.request_id = request_id
        
        # Add to logger context
        logger.debug(f"Processing request {request_id} for {request.method} {request.url.path}")
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response