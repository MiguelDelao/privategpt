from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict

import structlog

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

_renderer = structlog.processors.JSONRenderer()
_formatter = structlog.stdlib.ProcessorFormatter(
    processor=_renderer,
    foreign_pre_chain=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ],
)

_handler = logging.StreamHandler()
_handler.setFormatter(_formatter)
_root = logging.getLogger()
if not _root.hasHandlers():
    _root.addHandler(_handler)
    _root.setLevel(logging.INFO)


def get_logger(name: str):
    return structlog.get_logger(name)


def _clean(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


async def log_audit_event(user_email: str, event_type: str, event_data: Dict[str, Any]):
    log = get_logger("audit")
    payload = _clean(
        {
            "event_type": event_type,
            "user_email": user_email,
            "service": os.getenv("SERVICE_NAME", "unknown"),
            "environment": os.getenv("ENVIRONMENT", "dev"),
            "event_id": str(uuid.uuid4()),
            **event_data,
        }
    )
    log.info("audit", **payload)


async def log_security_event(event_type: str, event_data: Dict[str, Any]):
    log = get_logger("security")
    severity = event_data.get("severity", "info")
    payload = _clean(
        {
            "event_type": event_type,
            "severity": severity,
            "service": os.getenv("SERVICE_NAME", "unknown"),
            "environment": os.getenv("ENVIRONMENT", "dev"),
            "event_id": str(uuid.uuid4()),
            **event_data,
        }
    )
    if severity in {"high", "critical"}:
        log.warning("security", **payload)
    else:
        log.info("security", **payload) 