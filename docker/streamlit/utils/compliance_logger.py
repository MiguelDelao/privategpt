"""
Compliance logging utilities for PrivateGPT Legal AI
Handles audit trails and compliance monitoring from the UI
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class ComplianceLogger:
    """Compliance and audit logging for Streamlit application"""
    
    def __init__(self):
        self.log_dir = Path("/app/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Compliance log files
        self.audit_log = self.log_dir / "ui_audit.jsonl"
        self.interaction_log = self.log_dir / "ai_interactions.jsonl"
        self.document_log = self.log_dir / "document_operations.jsonl"
    
    def log_document_upload(
        self,
        user_email: str,
        document_id: str,
        filename: str,
        client_matter: str,
        file_size: Optional[int] = None,
        doc_type: Optional[str] = None
    ):
        """Log document upload event"""
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "document_upload",
            "service": "streamlit-ui",
            "message": f"User {user_email} uploaded document '{filename}' ({file_size or 'unknown size'} bytes)",
            "user_email": user_email,
            "document_id": document_id,
            "filename": filename,
            "client_matter": client_matter,
            "file_size": file_size,
            "document_type": doc_type
        }
        
        self._write_log(self.document_log, event)
    
    def log_ai_interaction(
        self,
        user_email: str,
        query: str,
        response_tokens: int,
        sources_accessed: List[str],
        client_matter: Optional[str] = None,
        response_time_ms: Optional[int] = None
    ):
        """Log AI interaction for compliance and billing"""
        # Sanitize query (remove PII, limit length)
        sanitized_query = self._sanitize_query(query)
        query_preview = sanitized_query[:50] + "..." if len(sanitized_query) > 50 else sanitized_query
        
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "ai_interaction",
            "service": "streamlit-ui",
            "message": f"User {user_email} asked: '{query_preview}' (generated {response_tokens} tokens)",
            "user_email": user_email,
            "query_sanitized": sanitized_query,
            "response_tokens": response_tokens,
            "sources_accessed": sources_accessed,
            "client_matter": client_matter,
            "response_time_ms": response_time_ms
        }
        
        self._write_log(self.interaction_log, event)
    
    def log_document_search(
        self,
        user_email: str,
        search_query: str,
        results_count: int,
        client_matter: Optional[str] = None
    ):
        """Log document search events"""
        query_preview = search_query[:30] + "..." if len(search_query) > 30 else search_query
        
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "document_search",
            "service": "streamlit-ui",
            "message": f"User {user_email} searched for '{query_preview}' (found {results_count} results)",
            "user_email": user_email,
            "search_query": self._sanitize_query(search_query),
            "results_count": results_count,
            "client_matter": client_matter
        }
        
        self._write_log(self.document_log, event)
    
    def log_user_session(
        self,
        user_email: str,
        session_action: str,  # login, logout, timeout
        session_duration_seconds: Optional[int] = None,
        client_ip: Optional[str] = None
    ):
        """Log user session events"""
        if session_action == "login":
            message = f"User {user_email} logged in successfully"
        elif session_action == "logout":
            duration = f" (session lasted {session_duration_seconds//60}m {session_duration_seconds%60}s)" if session_duration_seconds else ""
            message = f"User {user_email} logged out{duration}"
        elif session_action == "timeout":
            message = f"User {user_email} session timed out after {session_duration_seconds//60} minutes"
        else:
            message = f"User {user_email} session {session_action}"
            
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "user_session",
            "service": "streamlit-ui",
            "message": message,
            "user_email": user_email,
            "session_action": session_action,
            "session_duration_seconds": session_duration_seconds,
            "client_ip": client_ip
        }
        
        self._write_log(self.audit_log, event)
    
    def log_admin_action(
        self,
        admin_email: str,
        action_type: str,
        target_user: Optional[str] = None,
        action_details: Optional[Dict] = None
    ):
        """Log administrative actions"""
        if target_user:
            message = f"Admin {admin_email} performed '{action_type}' on user {target_user}"
        else:
            message = f"Admin {admin_email} performed administrative action: {action_type}"
            
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "admin_action",
            "service": "streamlit-ui",
            "message": message,
            "admin_email": admin_email,
            "action_type": action_type,
            "target_user": target_user,
            "action_details": action_details or {}
        }
        
        self._write_log(self.audit_log, event)
    
    def log_compliance_violation(
        self,
        user_email: str,
        violation_type: str,
        violation_details: str,
        severity: str = "medium"
    ):
        """Log compliance violations"""
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "compliance_violation",
            "service": "streamlit-ui",
            "message": f"COMPLIANCE VIOLATION ({severity.upper()}): User {user_email} - {violation_type}",
            "user_email": user_email,
            "violation_type": violation_type,
            "violation_details": violation_details,
            "severity": severity
        }
        
        self._write_log(self.audit_log, event)
    
    def get_user_activity_summary(self, user_email: str, days: int = 30) -> Dict:
        """Get summary of user activity for compliance reporting"""
        # This would typically query a database, but for MVP we'll return sample data
        return {
            "user_email": user_email,
            "period_days": days,
            "total_queries": 45,
            "documents_uploaded": 8,
            "documents_accessed": 23,
            "billable_hours": 12.5,
            "client_matters": ["ClientA_Contract2024", "ClientB_Litigation2024"],
            "compliance_score": 98.5
        }
    
    def _sanitize_query(self, query: str) -> str:
        """Sanitize query for logging (remove PII, limit length)"""
        # Basic PII patterns (extend as needed)
        import re
        
        # Remove email addresses
        query = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', query)
        
        # Remove phone numbers
        query = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', query)
        
        # Remove SSN patterns
        query = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', query)
        
        # Limit length
        if len(query) > 200:
            query = query[:200] + "..."
        
        return query
    
    def _write_log(self, log_file: Path, event: Dict):
        """Write event to log file"""
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            # Fallback logging - write to a backup file
            backup_log = self.log_dir / "compliance_backup.jsonl"
            with open(backup_log, 'a', encoding='utf-8') as f:
                error_event = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "error": f"Failed to write to {log_file}: {str(e)}",
                    "original_event": event
                }
                f.write(json.dumps(error_event) + '\n')
    
    def health_check(self) -> Dict:
        """Check health of compliance logging system"""
        try:
            # Test write capability
            test_file = self.log_dir / "health_check.log"
            with open(test_file, 'w') as f:
                f.write("health_check")
            test_file.unlink()  # Clean up
            
            return {
                "status": "healthy",
                "log_directory": str(self.log_dir),
                "writable": True
            }
        except Exception as e:
            return {
                "status": "error",
                "log_directory": str(self.log_dir),
                "writable": False,
                "error": str(e)
            } 