from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict

# *structlog* is optional in some dev environments (e.g. CI without extra deps).
# Provide a graceful fallback using the stdlib logging module if import fails.

try:
    import structlog  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – lightweight replacement
    import types

    structlog = types.ModuleType("structlog")  # type: ignore

    class _BoundLogger(logging.Logger):
        def bind(self, **_: object):  # noqa: D401 – mimic structlog API
            return self

    def get_logger(name: str):  # type: ignore
        return _BoundLogger(name)

    # attach minimal attributes used below
    structlog.get_logger = get_logger  # type: ignore
    class _ProcessorFormatter:
        def __init__(self, *args, **kwargs):  # noqa: D401
            pass

        @staticmethod
        def wrap_for_formatter(x):  # noqa: D401
            return x

    structlog.stdlib = types.SimpleNamespace(  # type: ignore
        add_logger_name=lambda *a, **k: None,
        add_log_level=lambda *a, **k: None,
        PositionalArgumentsFormatter=lambda *a, **k: None,
        LoggerFactory=lambda *a, **k: logging.getLogger,
        BoundLogger=_BoundLogger,
        ProcessorFormatter=_ProcessorFormatter,
    )
    structlog.processors = types.SimpleNamespace(
        TimeStamper=lambda *a, **k: None,
        StackInfoRenderer=lambda *a, **k: None,
        format_exc_info=lambda *a, **k: None,
        UnicodeDecoder=lambda *a, **k: None,
        JSONRenderer=lambda *a, **k: (lambda *a, **k: None),
    )
    structlog.contextvars = types.SimpleNamespace(
        bind_contextvars=lambda **kwargs: None,
        unbind_contextvars=lambda *args: None,
        get=lambda key, default=None: default,
    )
    structlog.configure = lambda **_: None  # type: ignore

# at this point *structlog* is guaranteed to be importable

_SERVICE_NAME = os.getenv("SERVICE_NAME", "unknown")


def _inject_service(logger, method, event_dict):  # noqa: D401
    event_dict.setdefault("service", _SERVICE_NAME)
    return event_dict


def _inject_request_id(logger, method, event_dict):  # noqa: D401
    # FastAPI request-id set by log middleware
    # structlog>=25 changed API; use get_contextvars when available
    try:
        request_id = structlog.contextvars.get("request_id", None)  # type: ignore[attr-defined]
    except AttributeError:
        request_id = structlog.contextvars.get_contextvars().get("request_id")  # type: ignore[attr-defined]
    if request_id:
        event_dict.setdefault("request_id", request_id)
    return event_dict


structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _inject_service,
        _inject_request_id,
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