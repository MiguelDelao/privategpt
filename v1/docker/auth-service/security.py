"""
PrivateGPT Legal AI - Security Service
Advanced password policies, JWT tokens, rate limiting, and session management
"""

import os
import hashlib
import secrets
import bcrypt
from jose import jwt
import redis
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import User, LoginSession, SecurityMetric

# Security configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "admin123456789abcdef")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))

# Rate limiting configuration
RATE_LIMIT_WINDOW_MINUTES = 15
MAX_LOGIN_ATTEMPTS = 10
LOCKOUT_DURATION_MINUTES = 30

# Redis configuration for rate limiting and sessions
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/3")

class SecurityService:
    """Comprehensive security service for authentication and authorization"""
    
    def __init__(self):
        """Initialize security service with Redis connection"""
        try:
            self.redis_client = redis.from_url(REDIS_URL)
            # Test connection
            self.redis_client.ping()
        except Exception as e:
            print(f"Warning: Redis connection failed: {e}")
            self.redis_client = None
    
    # Password Management
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt with configurable rounds"""
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    # JWT Token Management
    def create_jwt_token(self, user_data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT token with user data"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
        
        # Include standard JWT claims
        payload = {
            "sub": user_data.get("email"),  # Subject
            "exp": expire,  # Expiration
            "iat": datetime.utcnow(),  # Issued at
            "jti": self.generate_secure_token(16),  # JWT ID for revocation
            **user_data  # User data
        }
        
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    def create_access_token(self, user_data: Dict[str, Any], client_ip: str) -> Dict[str, Any]:
        """Create access token with user data"""
        expires_delta = timedelta(hours=JWT_EXPIRY_HOURS)
        token = self.create_jwt_token(user_data, expires_delta)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": JWT_EXPIRY_HOURS * 3600
        }
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    # Rate Limiting
    def check_rate_limit(self, identifier: str, max_attempts: int = MAX_LOGIN_ATTEMPTS, 
                        window_minutes: int = RATE_LIMIT_WINDOW_MINUTES) -> bool:
        """Check if identifier is within rate limits"""
        if not self.redis_client:
            return True  # Allow if Redis is down
        
        try:
            # Use sliding window rate limiting
            now = datetime.utcnow()
            window_start = int((now.timestamp() // (window_minutes * 60)) * (window_minutes * 60))
            key = f"rate_limit:{identifier}:{window_start}"
            
            current_count = self.redis_client.incr(key)
            if current_count == 1:
                self.redis_client.expire(key, window_minutes * 60)
            
            return current_count <= max_attempts
        except Exception:
            # If Redis is down, allow request but log warning
            return True
    
    def record_failed_login(self, email: str, ip_address: str) -> bool:
        """Record failed login attempt and check for lockout"""
        if not self.redis_client:
            return False
        
        try:
            # Track by email and IP separately
            email_key = f"failed_login:email:{email}"
            ip_key = f"failed_login:ip:{ip_address}"
            
            email_attempts = self.redis_client.incr(email_key)
            if email_attempts == 1:
                self.redis_client.expire(email_key, RATE_LIMIT_WINDOW_MINUTES * 60)
            
            ip_attempts = self.redis_client.incr(ip_key)
            if ip_attempts == 1:
                self.redis_client.expire(ip_key, RATE_LIMIT_WINDOW_MINUTES * 60)
            
            # Lock account if too many attempts
            if email_attempts >= MAX_LOGIN_ATTEMPTS:
                lockout_key = f"lockout:{email}"
                self.redis_client.setex(lockout_key, LOCKOUT_DURATION_MINUTES * 60, "locked")
                return True
            
            return False
        except Exception:
            return False
    
    def is_account_locked(self, email: str) -> bool:
        """Check if account is currently locked"""
        if not self.redis_client:
            return False
        
        lockout_key = f"lockout:{email}"
        return self.redis_client.exists(lockout_key)
    
    def clear_failed_attempts(self, email: str) -> None:
        """Clear failed login attempts for user"""
        if not self.redis_client:
            return
        
        email_key = f"failed_login:email:{email}"
        self.redis_client.delete(email_key)
    
    # Session Management
    def create_session(self, user_data: Dict[str, Any], ip_address: str, user_agent: str) -> str:
        """Create new login session"""
        if not self.redis_client:
            return None
        
        session_id = self.generate_secure_token(32)
        session_data = {
            "user_email": user_data.get("email"),
            "user_role": user_data.get("role"),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        
        try:
            # Store session data
            session_key = f"session:{session_id}"
            token_key = f"token:{user_data.get('jti', '')}"
            
            self.redis_client.setex(session_key, JWT_EXPIRY_HOURS * 3600, str(session_data))
            self.redis_client.setex(token_key, JWT_EXPIRY_HOURS * 3600, "active")
            
            return session_id
        except Exception:
            return None
    
    def validate_session(self, session_id: str, jti: str) -> bool:
        """Validate active session"""
        if not self.redis_client:
            return True  # Allow if Redis is down
        
        try:
            session_key = f"session:{session_id}"
            token_key = f"token:{jti}"
            
            # Check if both session and token exist
            if jti and not self.redis_client.exists(token_key):
                return False
            
            return self.redis_client.exists(session_key)
        except Exception:
            return True
    
    def revoke_session(self, session_id: str, jti: str) -> None:
        """Revoke/logout session"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.delete(f"token:{jti}")
            if session_id:
                self.redis_client.delete(f"session:{session_id}")
        except Exception:
            pass
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count"""
        if not self.redis_client:
            return 0
        
        try:
            count = 0
            # Clean up expired session keys
            pattern = "session:*"
            for key in self.redis_client.scan_iter(match=pattern):
                session_data = self.redis_client.get(key)
                if not session_data:
                    self.redis_client.delete(key)
                    count += 1
            
            # Clean up expired token keys
            pattern = "token:*"
            for key in self.redis_client.scan_iter(match=pattern):
                if not self.redis_client.exists(key):
                    self.redis_client.delete(key)
                    count += 1
            
            return count
        except Exception:
            return 0
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        if not self.redis_client:
            return None
        
        try:
            session_key = f"session:{session_id}"
            session_data = self.redis_client.get(session_key)
            if session_data:
                return eval(session_data)  # Convert string back to dict
            return None
        except Exception:
            return None
    
    def extend_session(self, session_id: str, jti: str) -> bool:
        """Extend session expiry"""
        if not self.redis_client:
            return True
        
        try:
            session_key = f"session:{session_id}"
            token_key = f"token:{jti}"
            
            new_expiry = JWT_EXPIRY_HOURS * 3600
            self.redis_client.expire(session_key, new_expiry)
            self.redis_client.expire(token_key, new_expiry)
            
            return True
        except Exception:
            return False
    
    # Security Metrics
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get current security metrics"""
        if not self.redis_client:
            return {}
        
        try:
            metrics = {}
            
            # Count active sessions
            pattern = "session:*"
            metrics["active_sessions"] = len(list(self.redis_client.scan_iter(match=pattern)))
            
            # Count locked accounts
            pattern = "lockout:*"
            metrics["locked_accounts"] = len(list(self.redis_client.scan_iter(match=pattern)))
            
            return metrics
        except Exception:
            return {}

# Global security service instance
security_service = SecurityService()

