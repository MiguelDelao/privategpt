"""
Utility classes for legal compliance, audit logging, and security monitoring
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import structlog
from pythonjsonlogger import jsonlogger

class AuditLogger:
    """Comprehensive audit logging for legal compliance"""
    
    def __init__(self):
        self.log_dir = Path("/app/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure structured JSON logging
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s'
        )
        
        # Configure logger
        self.logger = structlog.get_logger("audit")
        
    def log_auth_event(
        self,
        event_type: str,
        user_email: str,
        request_id: str,
        user_role: Optional[str] = None,
        reason: Optional[str] = None,
        action: Optional[str] = None,
        target_user: Optional[str] = None,
        created_by: Optional[str] = None,
        updated_by: Optional[str] = None,
        **kwargs
    ):
        """Log authentication events with legal compliance structure"""
        
        # Create human-readable message based on event type
        if event_type == "login_success":
            message = f"User {user_email} logged in successfully"
        elif event_type == "login_failure":
            message = f"Failed login attempt for {user_email}" + (f" - {reason}" if reason else "")
        elif event_type == "logout":
            message = f"User {user_email} logged out"
        elif event_type == "password_change":
            message = f"User {user_email} changed their password"
        elif event_type == "account_locked":
            message = f"Account {user_email} was locked" + (f" - {reason}" if reason else "")
        elif event_type == "user_created":
            message = f"New user account created: {user_email}" + (f" by {created_by}" if created_by else "")
        elif event_type == "user_updated":
            message = f"User account updated: {user_email}" + (f" by {updated_by}" if updated_by else "")
        elif event_type == "permission_granted":
            message = f"Permission '{action}' granted to {user_email}"
        elif event_type == "permission_denied":
            message = f"Permission '{action}' denied for {user_email}" + (f" - {reason}" if reason else "")
        else:
            message = f"Auth event '{event_type}' for user {user_email}"
        
        event_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "service": "auth-service",
            "message": message,
            "request_id": request_id,
            "user_email": user_email
        }
        
        # Add optional fields
        if user_role:
            event_data["user_role"] = user_role
        if reason:
            event_data["reason"] = reason
        if action:
            event_data["action"] = action
        if target_user:
            event_data["target_user"] = target_user
        if created_by:
            event_data["created_by"] = created_by
        if updated_by:
            event_data["updated_by"] = updated_by
            
        # Add any additional fields
        event_data.update(kwargs)
        
        # Write to structured log
        self.logger.info("auth_event", **event_data)
        
        # Also write to dedicated audit file
        audit_file = self.log_dir / f"audit_{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"
        with open(audit_file, 'a') as f:
            f.write(json.dumps(event_data) + '\n')

class SecurityMetrics:
    """Security metrics collection for monitoring and alerting"""
    
    def __init__(self):
        self.metrics_file = Path("/app/logs/security_metrics.json")
        self.failed_logins = {}
        self.successful_logins = {}
        
    def increment_failed_login(self, user_email: str):
        """Track failed login attempts"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        key = f"{user_email}_{today}"
        
        if key not in self.failed_logins:
            self.failed_logins[key] = 0
        self.failed_logins[key] += 1
        
        self._save_metrics()
        
        # Check for suspicious activity
        if self.failed_logins[key] >= 3:
            self._alert_suspicious_activity(user_email, "multiple_failed_logins")
    
    def increment_successful_login(self, user_email: str):
        """Track successful login attempts"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        key = f"{user_email}_{today}"
        
        if key not in self.successful_logins:
            self.successful_logins[key] = 0
        self.successful_logins[key] += 1
        
        self._save_metrics()
    
    def _save_metrics(self):
        """Save metrics to file"""
        metrics_data = {
            "failed_logins": self.failed_logins,
            "successful_logins": self.successful_logins,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        with open(self.metrics_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
    
    def _alert_suspicious_activity(self, user_email: str, activity_type: str):
        """Alert on suspicious security activity"""
        alert_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "alert_type": "security_incident",
            "severity": "high",
            "message": f"SECURITY ALERT: Multiple failed login attempts for {user_email}",
            "user_email": user_email,
            "activity_type": activity_type,
            "description": f"Suspicious activity detected for user {user_email}: {activity_type}"
        }
        
        # Log security alert
        logger = structlog.get_logger("security")
        logger.warning("security_alert", **alert_data)
        
        # Write to security alerts file
        alerts_file = Path("/app/logs") / f"security_alerts_{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"
        with open(alerts_file, 'a') as f:
            f.write(json.dumps(alert_data) + '\n')

class ComplianceMonitor:
    """Monitor compliance-related activities and policies"""
    
    def __init__(self):
        self.compliance_log = Path("/app/logs/compliance.jsonl")
        
    def log_data_access(
        self,
        user_email: str,
        document_id: str,
        client_matter: str,
        access_type: str = "read"
    ):
        """Log document access for compliance tracking"""
        
        access_event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "document_access",
            "message": f"User {user_email} {access_type} document {document_id} (matter: {client_matter})",
            "user_email": user_email,
            "document_id": document_id,
            "client_matter": client_matter,
            "access_type": access_type
        }
        
        with open(self.compliance_log, 'a') as f:
            f.write(json.dumps(access_event) + '\n')
    
    def log_ai_interaction(
        self,
        user_email: str,
        query: str,
        response_tokens: int,
        sources_accessed: list,
        client_matter: str = None
    ):
        """Log AI interactions for compliance and billing"""
        
        query_preview = query[:50] + "..." if len(query) > 50 else query
        sources_count = len(sources_accessed) if sources_accessed else 0
        
        ai_event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "ai_interaction",
            "message": f"User {user_email} asked: '{query_preview}' (generated {response_tokens} tokens, {sources_count} sources)",
            "user_email": user_email,
            "query_sanitized": query[:200] + "..." if len(query) > 200 else query,
            "response_tokens": response_tokens,
            "sources_accessed": sources_accessed,
            "client_matter": client_matter
        }
        
        with open(self.compliance_log, 'a') as f:
            f.write(json.dumps(ai_event) + '\n')

class DataRetentionManager:
    """Manage data retention policies for legal compliance"""
    
    def __init__(self):
        self.retention_policies = {
            "audit_logs": 2555,  # 7 years in days
            "user_data": 2555,
            "document_access": 2555,
            "ai_interactions": 2555,
            "security_logs": 2555
        }
    
    def cleanup_expired_data(self):
        """Clean up data that has exceeded retention periods"""
        # Implementation for data cleanup based on retention policies
        # This would be called by a scheduled job
        pass
    
    def verify_retention_compliance(self) -> Dict[str, bool]:
        """Verify that all data types are within retention policies"""
        compliance_status = {}
        
        for data_type, retention_days in self.retention_policies.items():
            # Check if data exists beyond retention period
            # Implementation depends on specific data storage patterns
            compliance_status[data_type] = True  # Placeholder
        
        return compliance_status 