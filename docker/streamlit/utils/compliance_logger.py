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
            "user_email": user_email,
            "document_id": document_id,
            "filename": filename,
            "client_matter": client_matter,
            "file_size": file_size,
            "document_type": doc_type,
            "compliance_metadata": {
                "data_classification": "confidential",
                "retention_policy": "7_years",
                "attorney_client_privilege": True,
                "billable_event": True
            },
            "compliance_tags": ["document_upload", "client_data", "billable_time"]
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
        
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "ai_interaction",
            "service": "streamlit-ui",
            "user_email": user_email,
            "query_sanitized": sanitized_query,
            "response_tokens": response_tokens,
            "sources_accessed": sources_accessed,
            "client_matter": client_matter,
            "response_time_ms": response_time_ms,
            "compliance_metadata": {
                "ai_assisted": True,
                "attorney_supervision": True,
                "data_classification": "confidential",
                "billable_event": True if client_matter else False,
                "requires_review": True
            },
            "compliance_tags": ["ai_interaction", "legal_research", "attorney_tools"]
        }
        
        if client_matter:
            event["compliance_tags"].append("billable_time")
        
        self._write_log(self.interaction_log, event)
    
    def log_document_search(
        self,
        user_email: str,
        search_query: str,
        results_count: int,
        client_matter: Optional[str] = None
    ):
        """Log document search events"""
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "document_search",
            "service": "streamlit-ui",
            "user_email": user_email,
            "search_query": self._sanitize_query(search_query),
            "results_count": results_count,
            "client_matter": client_matter,
            "compliance_metadata": {
                "data_classification": "confidential",
                "attorney_client_privilege": True,
                "billable_event": True if client_matter else False
            },
            "compliance_tags": ["document_search", "research_activity"]
        }
        
        if client_matter:
            event["compliance_tags"].append("billable_time")
        
        self._write_log(self.document_log, event)
    
    def log_user_session(
        self,
        user_email: str,
        session_action: str,  # login, logout, timeout
        session_duration_seconds: Optional[int] = None,
        client_ip: Optional[str] = None
    ):
        """Log user session events"""
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "user_session",
            "service": "streamlit-ui",
            "user_email": user_email,
            "session_action": session_action,
            "session_duration_seconds": session_duration_seconds,
            "client_ip": client_ip,
            "compliance_metadata": {
                "access_control": True,
                "security_relevant": True,
                "audit_trail": True
            },
            "compliance_tags": ["user_session", "access_control", "security"]
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
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": "admin_action",
            "service": "streamlit-ui",
            "admin_email": admin_email,
            "action_type": action_type,
            "target_user": target_user,
            "action_details": action_details or {},
            "compliance_metadata": {
                "privileged_operation": True,
                "security_relevant": True,
                "audit_trail": True,
                "requires_approval": False
            },
            "compliance_tags": ["admin_action", "privileged_access", "system_management"]
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
            "user_email": user_email,
            "violation_type": violation_type,
            "violation_details": violation_details,
            "severity": severity,
            "compliance_metadata": {
                "security_incident": True,
                "requires_investigation": True,
                "escalation_required": severity in ["high", "critical"]
            },
            "compliance_tags": ["compliance_violation", "security_incident", "investigation_required"]
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