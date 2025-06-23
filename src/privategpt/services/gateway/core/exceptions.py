"""
Custom exceptions for gateway services with standardized error handling.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime


class BaseServiceError(Exception):
    """Base exception for all service errors with standardized structure."""
    
    error_type: str = "service_error"
    error_code: str = "INTERNAL_ERROR"
    status_code: int = 500
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.suggestions = suggestions or []
        self.timestamp = datetime.utcnow()
    
    def to_dict(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Convert exception to standardized error response format."""
        error_dict = {
            "error": {
                "type": self.error_type,
                "code": self.error_code,
                "message": self.message,
                "timestamp": self.timestamp.isoformat()
            }
        }
        
        if self.details:
            error_dict["error"]["details"] = self.details
            
        if self.suggestions:
            error_dict["error"]["suggestions"] = self.suggestions
            
        if request_id:
            error_dict["error"]["request_id"] = request_id
            
        return error_dict


class ChatContextLimitError(BaseServiceError):
    """Raised when a chat request would exceed the model's context limit."""
    
    error_type = "context_limit_error"
    error_code = "CONTEXT_LIMIT_EXCEEDED"
    status_code = 413  # Payload Too Large
    
    def __init__(self, message: str, current_tokens: int, limit: int, model_name: str):
        super().__init__(
            message=message,
            details={
                "current_tokens": current_tokens,
                "limit": limit,
                "model_name": model_name
            },
            suggestions=[
                "Start a new conversation",
                f"Use a model with larger context (current: {limit} tokens)",
                "Shorten your message",
                "Clear some messages from the conversation history"
            ]
        )
        self.current_tokens = current_tokens
        self.limit = limit
        self.model_name = model_name


class ResourceExhaustedError(BaseServiceError):
    """Raised when system resources (memory, compute) are exhausted."""
    
    error_type = "resource_error"
    error_code = "RESOURCE_EXHAUSTED"
    status_code = 503  # Service Unavailable
    
    def __init__(self, message: str, resource_type: str, model_name: Optional[str] = None):
        details = {"resource_type": resource_type}
        if model_name:
            details["model_name"] = model_name
            
        suggestions = []
        if resource_type == "memory":
            suggestions = [
                "Try a smaller model",
                "Reduce the max_tokens parameter",
                "Wait a few minutes and retry"
            ]
        elif resource_type == "compute":
            suggestions = [
                "The service is under heavy load",
                "Try again in a few minutes",
                "Consider using a different model"
            ]
            
        super().__init__(
            message=message,
            details=details,
            suggestions=suggestions
        )


class ModelNotAvailableError(BaseServiceError):
    """Raised when a requested model is not available."""
    
    error_type = "model_error"
    error_code = "MODEL_NOT_AVAILABLE"
    status_code = 404  # Not Found
    
    def __init__(self, model_name: str, available_models: Optional[List[str]] = None):
        details = {"requested_model": model_name}
        suggestions = ["Check the model name spelling"]
        
        if available_models:
            details["available_models"] = available_models
            suggestions.append(f"Try one of: {', '.join(available_models[:5])}")
            
        super().__init__(
            message=f"Model '{model_name}' is not available",
            details=details,
            suggestions=suggestions
        )


class ValidationError(BaseServiceError):
    """Raised when input validation fails."""
    
    error_type = "validation_error"
    error_code = "INVALID_INPUT"
    status_code = 400  # Bad Request
    
    def __init__(self, message: str, field: Optional[str] = None, constraints: Optional[Dict[str, Any]] = None):
        details = {}
        if field:
            details["field"] = field
        if constraints:
            details["constraints"] = constraints
            
        super().__init__(
            message=message,
            details=details,
            suggestions=["Check the input format", "Refer to API documentation"]
        )


class RateLimitError(BaseServiceError):
    """Raised when rate limits are exceeded."""
    
    error_type = "rate_limit_error"
    error_code = "RATE_LIMIT_EXCEEDED"
    status_code = 429  # Too Many Requests
    
    def __init__(self, message: str, retry_after: Optional[int] = None, limit: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        if limit:
            details["limit"] = limit
            
        super().__init__(
            message=message,
            details=details,
            suggestions=[
                "Reduce request frequency",
                f"Wait {retry_after} seconds before retrying" if retry_after else "Wait before retrying"
            ]
        )


class ServiceUnavailableError(BaseServiceError):
    """Raised when a downstream service is unavailable."""
    
    error_type = "service_unavailable"
    error_code = "SERVICE_UNAVAILABLE"
    status_code = 503  # Service Unavailable
    
    def __init__(self, service_name: str, reason: Optional[str] = None):
        details = {"service": service_name}
        if reason:
            details["reason"] = reason
            
        super().__init__(
            message=f"{service_name} service is currently unavailable",
            details=details,
            suggestions=[
                "Try again in a few moments",
                "Check service status",
                "Contact support if the issue persists"
            ]
        )


class ConfigurationError(BaseServiceError):
    """Raised when there are configuration issues."""
    
    error_type = "configuration_error"
    error_code = "CONFIG_ERROR"
    status_code = 500  # Internal Server Error
    
    def __init__(self, message: str, missing_config: Optional[str] = None):
        details = {}
        if missing_config:
            details["missing_config"] = missing_config
            
        super().__init__(
            message=message,
            details=details,
            suggestions=[
                "Check environment variables",
                "Verify configuration files",
                "Contact system administrator"
            ]
        )