"""
Utility functions for the auth service - simplified structured logging
"""

import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import structlog

# Configure structlog for JSON output
structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# JSON formatter for structured logging
json_renderer = structlog.processors.JSONRenderer()
stdlib_formatter = structlog.stdlib.ProcessorFormatter(
    processor=json_renderer,
    foreign_pre_chain=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
)

# Configure root logger
handler = logging.StreamHandler()
handler.setFormatter(stdlib_formatter)
root_logger = logging.getLogger()
if not root_logger.hasHandlers():
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

def get_logger(name: str):
    """Get a structlog logger instance"""
    return structlog.get_logger(name)

def clean_dict(data: dict) -> dict:
    """Remove None values from dictionary"""
    return {k: v for k, v in data.items() if v is not None}

async def log_audit_event(
    user_email: str,
    event_type: str, 
    event_data: Dict[str, Any], 
    db=None  # Kept for compatibility
):
    """Log audit events with structured logging"""
    log = get_logger("auth_service.audit")
    
    payload = {
        "event_type": event_type,
        "user_email": user_email,
        "service": "auth-service",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "event_id": str(uuid.uuid4()),
        **clean_dict(event_data)
    }
    
    log.info(f"Audit: {event_type} for {user_email}", **payload)

async def log_security_event(
    event_type: str, 
    event_data: Dict[str, Any], 
    db=None  # Kept for compatibility
):
    """Log security events with structured logging"""
    log = get_logger("auth_service.security")
    
    severity = event_data.get("severity", "info")
    user_email = event_data.get("user_email", "unknown")
    
    payload = {
        "event_type": event_type,
        "severity": severity,
        "user_email": user_email,
        "service": "auth-service",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "event_id": str(uuid.uuid4()),
        **clean_dict(event_data)
    }
    
    message = f"Security: {event_type}"
    if severity in ["high", "critical"]:
        log.warning(message, **payload)
    else:
        log.info(message, **payload)

# Example of how to log a simple metric if needed by other parts of auth_service.py
# (This is not directly replacing a part of the old log_security_event, but shows how metrics could be handled)
# async def log_metric(metric_name: str, value: Any, **kwargs):
#     log = get_logger("auth_service.metrics")
#     payload = {
#         "event_category": "metric",
#         "metric_name": metric_name,
#         "metric_value": value,
#         "service": "auth-service",
#         **kwargs
#     }
#     log.info(f"Metric: {metric_name} = {value}", **_clean_none_values_global(payload)) 