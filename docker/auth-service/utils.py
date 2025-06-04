"""
Utility functions for the auth service, focusing on structured logging.
"""

import os
import json # Kept for potential future use, though not directly by logging now
import uuid
from datetime import datetime # Kept for direct use if constructing timestamps manually
from typing import Dict, Any, Optional
import logging
import structlog

# Configure structlog globally
structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.set_exc_info, # Adds exc_info=True to log calls with exceptions
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Configure the underlying Python logging to output JSON
# This is where the final formatting to JSON happens

# The processor that will render the event_dict to a JSON string.
# This is used for logs processed by the standard library handler.
json_renderer_for_stdlib = structlog.processors.JSONRenderer()

# This formatter is for the standard library logging handler.
# It processes log records (both from structlog and foreign logs).
stdlib_formatter = structlog.stdlib.ProcessorFormatter(
    processor=json_renderer_for_stdlib,  # Main processor to render the final event dict
    # Processors in foreign_pre_chain are applied to LogRecords
    # from non-structlog loggers before they are passed to the main processor.
    foreign_pre_chain=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
)

handler = logging.StreamHandler()
handler.setFormatter(stdlib_formatter) # Use the direct ProcessorFormatter instance
root_logger = logging.getLogger()
if not root_logger.hasHandlers(): # Avoid adding handler multiple times if script reloaded
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def get_logger(name: str):
    """Get a structlog logger instance."""
    return structlog.get_logger(name)

def _clean_none_values_global(data: dict) -> dict:
    """Remove None values from nested dictionary. For global use."""
    cleaned = {}
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                cleaned_v = _clean_none_values_global(v)
                if cleaned_v: 
                    cleaned[k] = cleaned_v
            elif v is not None:
                cleaned[k] = v
        return cleaned
    return data

# Removed AuditLogger, SecurityMetrics, ComplianceMonitor, DataRetentionManager classes
# Removed their global instantiations (audit_logger, security_metrics, etc.)

async def log_audit_event(
    user_email: str, # Changed from user_id to user_email for clarity, assuming it's email
    event_type: str, 
    event_data: Dict[str, Any], 
    db=None # db parameter kept for signature compatibility, though not used in this simplified version
):
    """Log audit events directly using structlog."""
    log = get_logger("auth_service.audit") # Specific logger name for audit events

    # Construct human-readable message
    # (This part can be expanded based on event_type as previously in AuditLogger)
    default_message = f"Audit event '{event_type}' for user {user_email}"
    message_map = {
        "login_success": f"User {user_email} logged in successfully",
        "login_failed": f"Failed login attempt for {user_email}" + (f" - {event_data.get('reason')}" if event_data.get('reason') else ""),
        "logout": f"User {user_email} logged out",
        "password_change": f"User {user_email} changed their password",
        "account_locked": f"Account {user_email} was locked" + (f" - {event_data.get('reason')}" if event_data.get('reason') else ""),
        "user_created": f"New user account created: {user_email}" + (f" by {event_data.get('created_by')}" if event_data.get('created_by') else ""),
        "user_updated": f"User account updated: {user_email}" + (f" by {event_data.get('updated_by')}" if event_data.get('updated_by') else ""),
        "permission_granted": f"Permission '{event_data.get('action')}' granted to {user_email}",
        "permission_denied": f"Permission '{event_data.get('action')}' denied for {user_email}" + (f" - {event_data.get('reason')}" if event_data.get('reason') else ""),
        "mfa_enabled": f"MFA enabled for user {user_email}",
        "mfa_disabled": f"MFA disabled for user {user_email}",
        "mfa_failed": f"MFA verification failed for {user_email}",
        "rate_limit_exceeded": f"Rate limit exceeded for {user_email}", # event_data might have more context
        "token_revoked": f"Token revoked for {user_email}",
        "unauthorized_action": f"Unauthorized action attempted by {user_email}"
    }
    log_message = message_map.get(event_type, default_message)

    payload = {
        "event_category": "authentication",
        "event_type": event_type,
        "user_email": user_email,
        "service": "auth-service",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "event_id": str(uuid.uuid4()),
        # Include fields from event_data, ensuring they don't overwrite core fields
        "details": event_data # Keep original event_data nested under details
    }
    
    # Add specific, known fields from event_data to the top level if desired, e.g.:
    if "request_id" in event_data: payload["request_id"] = event_data.pop("request_id")
    if "ip_address" in event_data: payload["ip_address"] = event_data.pop("ip_address")
    if "client_ip" in event_data and "ip_address" not in payload: payload["ip_address"] = event_data.pop("client_ip")
    if "user_agent" in event_data: payload["user_agent"] = event_data.pop("user_agent")
    if "session_id" in event_data: payload["session_id"] = event_data.pop("session_id")
    # ... and other relevant fields from the original AuditLogger.log_auth_event structure

    log.info(log_message, **_clean_none_values_global(payload))


async def log_security_event(
    event_type: str, 
    event_data: Dict[str, Any], 
    db=None # db parameter kept for signature compatibility
):
    """Log security-related events (alerts/metrics) directly using structlog."""
    log = get_logger("auth_service.security") # Specific logger name for security events

    severity = event_data.get("severity", "medium").lower()
    description = event_data.get("description", f"Security event: {event_type}")
    user_email = event_data.get("username") or event_data.get("user_email")
    ip_address = event_data.get("ip") or event_data.get("client_ip")
    
    log_message = f"SECURITY [{severity.upper()}]: {description}"
    if user_email: log_message += f" (User: {user_email})"
    if ip_address: log_message += f" (IP: {ip_address})"

    payload = {
        "event_category": "security_alert", # Could also be "security_metric" if differentiated
        "event_type": event_type,
        "severity": severity,
        "description": description, # The original description from event_data
        "user_email": user_email,
        "ip_address": ip_address,
        "service": "auth-service",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "event_id": str(uuid.uuid4()),
        "details": event_data # Keep original event_data nested under details
    }

    if severity in ["high", "critical"]:
        log.warning(log_message, **_clean_none_values_global(payload))
    else:
        log.info(log_message, **_clean_none_values_global(payload))

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