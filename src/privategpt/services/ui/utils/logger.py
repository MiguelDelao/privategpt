"""
Logging utilities for PrivateGPT UI (v2).
Currently the implementation mirrors the old v1 behaviour (flat-file logs in
/app/logs) so we keep API compatibility.  In production this will be replaced
by structured JSON logging to stdout harvested by Filebeat.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class Logger:  # noqa: D101
    def __init__(self):
        self.log_dir = Path("/app/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Simple log files
        self.activity_log = self.log_dir / "user_activity.log"
        self.error_log = self.log_dir / "errors.log"

    # ------------------------------------------------------------------
    # High-level helpers (unchanged from v1)
    # ------------------------------------------------------------------
    def log_user_login(
        self,
        user_email: str,
        success: bool = True,
        ip_address: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        if success:
            message = f"User {user_email} logged in successfully"
        else:
            base_message = f"Failed login attempt for {user_email}"
            message = f"{base_message}: {error_message}" if error_message else base_message

        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "user_login",
            "message": message,
            "user_email": user_email,
            "success": success,
            "ip_address": ip_address,
        }
        if error_message and not success:
            event["error_detail"] = error_message

        self._write_log(self.activity_log, event)

    def log_user_logout(self, user_email: str, session_duration_seconds: int | None = None) -> None:
        duration_text = (
            f" (session lasted {session_duration_seconds//60}m {session_duration_seconds%60}s)"
            if session_duration_seconds
            else ""
        )
        message = f"User {user_email} logged out{duration_text}"

        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "user_logout",
            "message": message,
            "user_email": user_email,
            "session_duration_seconds": session_duration_seconds,
        }
        self._write_log(self.activity_log, event)

    def log_document_upload(self, user_email: str, filename: str, file_size: int | None = None) -> None:
        size_text = f" ({self._format_bytes(file_size)})" if file_size else ""
        message = f"User {user_email} uploaded document '{filename}'{size_text}"
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "document_upload",
            "message": message,
            "user_email": user_email,
            "filename": filename,
            "file_size": file_size,
        }
        self._write_log(self.activity_log, event)

    def log_ai_query(
        self,
        user_email: str,
        query: str,
        response_tokens: int | None = None,
    ) -> None:
        query_preview = query[:60] + "..." if len(query) > 60 else query
        tokens_text = f" (generated {response_tokens} tokens)" if response_tokens else ""
        message = f"User {user_email} asked: '{query_preview}'{tokens_text}"
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "ai_query",
            "message": message,
            "user_email": user_email,
            "query": query,
            "response_tokens": response_tokens,
        }
        self._write_log(self.activity_log, event)

    def log_document_search(
        self,
        user_email: str,
        search_query: str,
        results_count: int = 0,
    ) -> None:
        query_preview = search_query[:40] + "..." if len(search_query) > 40 else search_query
        message = f"User {user_email} searched for '{query_preview}' (found {results_count} results)"
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "document_search",
            "message": message,
            "user_email": user_email,
            "search_query": search_query,
            "results_count": results_count,
        }
        self._write_log(self.activity_log, event)

    def log_error(
        self,
        user_email: str,
        error_message: str,
        error_type: str = "general",
    ) -> None:
        message = f"Error for user {user_email}: {error_message}"
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "error",
            "message": message,
            "user_email": user_email,
            "error_message": error_message,
            "error_type": error_type,
        }
        self._write_log(self.error_log, event)

    def log_page_view(self, user_email: str, page_name: str) -> None:
        message = f"User {user_email} navigated to {page_name}"
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "page_view",
            "message": message,
            "user_email": user_email,
            "page_name": page_name,
        }
        self._write_log(self.activity_log, event)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _format_bytes(self, bytes_size: int) -> str:  # noqa: D401
        if not bytes_size:
            return "unknown size"
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f}TB"

    def _write_log(self, log_file: Path, event: Dict) -> None:  # noqa: D401
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as exc:  # noqa: BLE001
            backup_log = self.log_dir / "backup.log"
            with open(backup_log, "a", encoding="utf-8") as f:
                error_event = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "error": f"Failed to write to {log_file}: {exc}",
                    "original_event": event,
                }
                f.write(json.dumps(error_event) + "\n") 