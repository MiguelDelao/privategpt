"""
Centralized error handling utilities for the gateway service.
"""
import logging
import traceback
from typing import Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from privategpt.services.gateway.core.exceptions import (
    BaseServiceError,
    ValidationError,
    ServiceUnavailableError,
    ConfigurationError,
    ResourceExhaustedError,
)

logger = logging.getLogger(__name__)


def get_request_id(request: Request) -> Optional[str]:
    """Extract request ID from request headers or state."""
    # Try to get from middleware-set state first
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return request_id
    
    # Fallback to header
    return request.headers.get("X-Request-ID")


async def service_error_handler(request: Request, exc: BaseServiceError) -> JSONResponse:
    """Handle custom service errors with standardized format."""
    request_id = get_request_id(request)
    
    # Log the error with context
    logger.error(
        f"{exc.error_code}: {exc.message}",
        extra={
            "error_type": exc.error_type,
            "error_code": exc.error_code,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )
    
    # Return standardized error response
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(request_id)
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPExceptions with standardized format."""
    request_id = get_request_id(request)
    
    # Map common HTTP errors to our format
    error_mapping = {
        400: ("validation_error", "BAD_REQUEST"),
        401: ("auth_error", "UNAUTHORIZED"),
        403: ("auth_error", "FORBIDDEN"),
        404: ("not_found", "NOT_FOUND"),
        409: ("conflict", "CONFLICT"),
        413: ("validation_error", "PAYLOAD_TOO_LARGE"),
        429: ("rate_limit_error", "RATE_LIMITED"),
        500: ("service_error", "INTERNAL_ERROR"),
        502: ("service_error", "BAD_GATEWAY"),
        503: ("service_error", "SERVICE_UNAVAILABLE"),
        504: ("service_error", "GATEWAY_TIMEOUT")
    }
    
    error_type, error_code = error_mapping.get(
        exc.status_code, 
        ("service_error", "UNKNOWN_ERROR")
    )
    
    # Log the error
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # Build standardized response
    error_dict = {
        "error": {
            "type": error_type,
            "code": error_code,
            "message": str(exc.detail),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    if request_id:
        error_dict["error"]["request_id"] = request_id
    
    # Add suggestions for common errors
    if exc.status_code == 401:
        error_dict["error"]["suggestions"] = [
            "Check your authentication credentials",
            "Ensure your token hasn't expired",
            "Login again to get a new token"
        ]
    elif exc.status_code == 404:
        error_dict["error"]["suggestions"] = [
            "Check the resource ID or path",
            "Ensure the resource exists",
            "Verify you have access to this resource"
        ]
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_dict
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors with standardized format."""
    request_id = get_request_id(request)
    
    # Extract validation errors
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"]
        })
    
    # Log the validation error
    logger.warning(
        f"Validation error: {len(errors)} field(s) failed validation",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "errors": errors
        }
    )
    
    # Build standardized response
    validation_exc = ValidationError(
        message=f"Request validation failed: {len(errors)} error(s)",
        field="request_body",
        constraints={"errors": errors}
    )
    
    return JSONResponse(
        status_code=validation_exc.status_code,
        content=validation_exc.to_dict(request_id)
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with standardized format."""
    request_id = get_request_id(request)
    
    # Check if this is a known error pattern
    error_str = str(exc).lower()
    
    # Parse common error patterns
    if "out of memory" in error_str or "oom" in error_str:
        service_exc = ResourceExhaustedError(
            message="Model ran out of memory while processing request",
            resource_type="memory"
        )
    elif "connection refused" in error_str or "connection error" in error_str:
        service_exc = ServiceUnavailableError(
            service_name="LLM Service",
            reason="Unable to connect to service"
        )
    elif "timeout" in error_str:
        service_exc = ServiceUnavailableError(
            service_name="LLM Service",
            reason="Request timed out"
        )
    elif "model not found" in error_str or "unknown model" in error_str:
        # Extract model name if possible
        import re
        model_match = re.search(r"model[:\s]+(['\"]?)([^'\"]+)\1", error_str, re.IGNORECASE)
        model_name = model_match.group(2) if model_match else "unknown"
        from privategpt.services.gateway.core.exceptions import ModelNotAvailableError
        service_exc = ModelNotAvailableError(model_name=model_name)
    else:
        # Generic internal error
        service_exc = BaseServiceError(
            message="An unexpected error occurred",
            details={"error_type": type(exc).__name__}
        )
    
    # Log the full error with traceback (but don't expose to user)
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }
    )
    
    # Return standardized error response
    return JSONResponse(
        status_code=service_exc.status_code,
        content=service_exc.to_dict(request_id)
    )


def should_hide_error_details() -> bool:
    """Check if error details should be hidden (production mode)."""
    import os
    env = os.getenv("ENVIRONMENT", "production").lower()
    return env in ["production", "prod"]


# Import datetime for error timestamps
from datetime import datetime