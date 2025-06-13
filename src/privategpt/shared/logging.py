"""Structured logging helpers shared across micro-services.

This is essentially a lightly-tweaked copy of the former
`docker/auth-service/utils.py` so all services can import the same helper:

    from privategpt.shared.logging import get_logger, log_audit_event, log_security_event
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, Optional

import structlog

# Configure structlog once – idempotent if called multiple times
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

json_renderer = structlog.processors.JSONRenderer()
_formatter = structlog.stdlib.ProcessorFormatter(
    processor=json_renderer,
    foreign_pre_chain=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ],
)

_handler = logging.StreamHandler()
_handler.setFormatter(_formatter)
_root_logger = logging.getLogger()
if not _root_logger.hasHandlers():
    _root_logger.addHandler(_handler)
    _root_logger.setLevel(logging.INFO)


def get_logger(name: str):  # noqa: D401 – factory fn is fine
    """Return a structlog logger bound to *name*."""

    return structlog.get_logger(name)


def _clean_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


async def log_audit_event(
    user_email: str,
    event_type: str,
    event_data: Dict[str, Any],
    db: Optional[object] = None,  # Compatibility placeholder
):
    log = get_logger("audit")
    payload = {
        "event_type": event_type,
        "user_email": user_email,
        "service": os.getenv("SERVICE_NAME", "unknown"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "event_id": str(uuid.uuid4()),
        **_clean_dict(event_data),
    }
    log.info(f"Audit: {event_type} for {user_email}", **payload)


async def log_security_event(
    event_type: str,
    event_data: Dict[str, Any],
    db: Optional[object] = None,  # Compatibility placeholder
):
    log = get_logger("security")
    severity = event_data.get("severity", "info")
    payload = {
        "event_type": event_type,
        "severity": severity,
        "service": os.getenv("SERVICE_NAME", "unknown"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "event_id": str(uuid.uuid4()),
        **_clean_dict(event_data),
    }

    if severity in {"high", "critical"}:
        log.warning(f"Security: {event_type}", **payload)
    else:
        log.info(f"Security: {event_type}", **payload) 