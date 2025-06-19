from __future__ import annotations

"""FastAPI middleware that adds a `request_id` and logs each request."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger("http")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        request_id = str(uuid.uuid4())
        # put into structlog context
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id  # type: ignore[attr-defined]

        start = time.time()
        logger.info(
            "http.request.start",
            method=request.method,
            path=request.url.path,
        )
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = int((time.time() - start) * 1000)
            status_code = getattr(response, "status_code", 500) if response else 500
            logger.info(
                "http.request.end",
                status=status_code,
                duration_ms=duration_ms,
            )
            structlog.contextvars.unbind_contextvars("request_id")