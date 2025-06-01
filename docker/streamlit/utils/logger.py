"""
 Logging utilities for PrivateGPT Legal AI
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class Logger:
    """Logging for PrivateGPT Legal AI"""
    
    def __init__(self):
        self.log_dir = Path("/app/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Simple log files
        self.activity_log = self.log_dir / "user_activity.log"
        self.error_log = self.log_dir / "errors.log"
    
    def log_user_login(self, user_email: str, success: bool = True, ip_address: str = None):
        """Log user login attempts"""
        if success:
            message = f"User {user_email} logged in successfully"
        else:
            message = f"Failed login attempt for {user_email}"
            
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "user_login",
            "message": message,
            "user_email": user_email,
            "success": success,
            "ip_address": ip_address
        }
        
        self._write_log(self.activity_log, event)
    
    def log_user_logout(self, user_email: str, session_duration_seconds: int = None):
        """Log user logout events"""
        duration_text = f" (session lasted {session_duration_seconds//60}m {session_duration_seconds%60}s)" if session_duration_seconds else ""
        message = f"User {user_email} logged out{duration_text}"
            
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "user_logout",
            "message": message,
            "user_email": user_email,
            "session_duration_seconds": session_duration_seconds
        }
        
        self._write_log(self.activity_log, event)
    
    def log_document_upload(self, user_email: str, filename: str, file_size: int = None):
        """Log document upload events"""
        size_text = f" ({self._format_bytes(file_size)})" if file_size else ""
        message = f"User {user_email} uploaded document '{filename}'{size_text}"
        
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "document_upload",
            "message": message,
            "user_email": user_email,
            "filename": filename,
            "file_size": file_size
        }
        
        self._write_log(self.activity_log, event)
    
    def log_ai_query(self, user_email: str, query: str, response_tokens: int = None):
        """Log AI interaction events"""
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
            "response_tokens": response_tokens
        }
        
        self._write_log(self.activity_log, event)
    
    def log_document_search(self, user_email: str, search_query: str, results_count: int = 0):
        """Log document search events"""
        query_preview = search_query[:40] + "..." if len(search_query) > 40 else search_query
        message = f"User {user_email} searched for '{query_preview}' (found {results_count} results)"
        
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "document_search",
            "message": message,
            "user_email": user_email,
            "search_query": search_query,
            "results_count": results_count
        }
        
        self._write_log(self.activity_log, event)
    
    def log_error(self, user_email: str, error_message: str, error_type: str = "general"):
        """Log application errors"""
        message = f"Error for user {user_email}: {error_message}"
        
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "error",
            "message": message,
            "user_email": user_email,
            "error_message": error_message,
            "error_type": error_type
        }
        
        self._write_log(self.error_log, event)
    
    def log_page_view(self, user_email: str, page_name: str):
        """Log page navigation events"""
        message = f"User {user_email} navigated to {page_name}"
        
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "page_view",
            "message": message,
            "user_email": user_email,
            "page_name": page_name
        }
        
        self._write_log(self.activity_log, event)
    
    def _format_bytes(self, bytes_size: int) -> str:
        """Format bytes into human readable format"""
        if not bytes_size:
            return "unknown size"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f}TB"
    
    def _write_log(self, log_file: Path, event: Dict):
        """Write event to log file"""
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            # Fallback logging
            backup_log = self.log_dir / "backup.log"
            with open(backup_log, 'a', encoding='utf-8') as f:
                error_event = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "error": f"Failed to write to {log_file}: {str(e)}",
                    "original_event": event
                }
                f.write(json.dumps(error_event) + '\n') 