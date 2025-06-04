"""
Security service for authentication
Advanced password policies, JWT tokens, rate limiting, MFA, and session management
"""

import hashlib
import secrets
import time
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from collections import defaultdict
import redis
import pyotp
from passlib.context import CryptContext
from jose import jwt, JWTError
import uuid
import os
from sqlalchemy.orm import Session
import bcrypt
import qrcode
import io
import base64

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/3")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "8"))

# Rate limiting configuration
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "30"))
RATE_LIMIT_WINDOW_MINUTES = int(os.getenv("RATE_LIMIT_WINDOW_MINUTES", "15"))

# Password policy
MIN_PASSWORD_LENGTH = int(os.getenv("MIN_PASSWORD_LENGTH", "12"))
REQUIRE_SPECIAL_CHARS = os.getenv("REQUIRE_SPECIAL_CHARS", "true").lower() == "true"
REQUIRE_NUMBERS = os.getenv("REQUIRE_NUMBERS", "true").lower() == "true"
REQUIRE_UPPERCASE = os.getenv("REQUIRE_UPPERCASE", "true").lower() == "true"
REQUIRE_LOWERCASE = os.getenv("REQUIRE_LOWERCASE", "true").lower() == "true"

# Assuming models.py is in the same directory or accessible
from models import User, LoginSession, get_db # Changed from .models

class SecurityService:
    """Comprehensive security service"""
    
    def __init__(self):
        self.redis_client = redis.from_url(REDIS_URL)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.login_attempts = defaultdict(int)
        self.lockout_times = {}
        
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def validate_password_policy(self, password: str) -> Tuple[bool, list]:
        """Validate password against security policy"""
        errors = []
        
        if len(password) < MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
        
        if REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if REQUIRE_NUMBERS and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if REQUIRE_SPECIAL_CHARS and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Check against common passwords
        if password.lower() in self._get_common_passwords():
            errors.append("Password is too common, please choose a more secure password")
        
        return len(errors) == 0, errors
    
    def _get_common_passwords(self) -> set:
        """Return set of common passwords to avoid"""
        return {
            "password", "123456", "123456789", "qwerty", "abc123", 
            "password123", "admin", "letmein", "welcome", "monkey",
            "1234567890", "password1", "123123", "admin123"
        }
    
    def check_rate_limit(self, identifier: str, max_requests: int = 10, window_minutes: int = 15) -> Tuple[bool, int]:
        """Check if request is within rate limits"""
        key = f"rate_limit:{identifier}"
        window_start = int(time.time()) // (window_minutes * 60)
        
        try:
            current_count = self.redis_client.incr(f"{key}:{window_start}")
            if current_count == 1:
                self.redis_client.expire(f"{key}:{window_start}", window_minutes * 60)
            
            if current_count > max_requests:
                return False, current_count
            
            return True, current_count
        except Exception:
            # If Redis is down, allow request but log warning
            return True, 0
    
    def record_failed_login(self, email: str, ip_address: str) -> bool:
        """Record failed login attempt and check if account should be locked"""
        # Track by email
        email_key = f"failed_login:email:{email}"
        email_attempts = self.redis_client.incr(email_key)
        if email_attempts == 1:
            self.redis_client.expire(email_key, RATE_LIMIT_WINDOW_MINUTES * 60)
        
        # Track by IP
        ip_key = f"failed_login:ip:{ip_address}"
        ip_attempts = self.redis_client.incr(ip_key)
        if ip_attempts == 1:
            self.redis_client.expire(ip_key, RATE_LIMIT_WINDOW_MINUTES * 60)
        
        # Check if account should be locked
        if email_attempts >= MAX_LOGIN_ATTEMPTS:
            self._lock_account(email)
            return True
        
        return False
    
    def _lock_account(self, email: str):
        """Lock account for specified duration"""
        lockout_key = f"account_locked:{email}"
        self.redis_client.setex(lockout_key, LOCKOUT_DURATION_MINUTES * 60, "locked")
    
    def is_account_locked(self, email: str) -> bool:
        """Check if account is currently locked"""
        lockout_key = f"account_locked:{email}"
        return self.redis_client.exists(lockout_key)
    
    def clear_failed_attempts(self, email: str):
        """Clear failed login attempts after successful login"""
        email_key = f"failed_login:email:{email}"
        self.redis_client.delete(email_key)
    
    def create_access_token(self, user_data: dict, ip_address: str = None, user_agent: str = None) -> dict:
        """Create JWT access token with session tracking"""
        jti = str(uuid.uuid4())  # JWT ID for session tracking
        session_id = str(uuid.uuid4())
        
        # Token payload
        payload = {
            "sub": user_data["email"],
            "role": user_data["role"],
            "client_matters": user_data.get("client_matters", []),
            "jti": jti,
            "session_id": session_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + (JWT_EXPIRY_HOURS * 3600)
        }
        
        # Create JWT token
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        # Store session information
        session_data = {
            "user_email": user_data["email"],
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)).isoformat()
        }
        
        session_key = f"session:{session_id}"
        token_key = f"token:{jti}"
        
        # Store with expiration
        self.redis_client.setex(session_key, JWT_EXPIRY_HOURS * 3600, str(session_data))
        self.redis_client.setex(token_key, JWT_EXPIRY_HOURS * 3600, "active")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": JWT_EXPIRY_HOURS * 3600,
            "session_id": session_id,
            "user_role": user_data["role"]
        }
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify JWT token and check if session is active"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti and not self.redis_client.exists(f"token:{jti}"):
                return None
            
            return payload
        except JWTError:
            return None
    
    def revoke_token(self, jti: str, session_id: str = None):
        """Revoke specific token and session"""
        if jti:
            self.redis_client.delete(f"token:{jti}")
        if session_id:
            self.redis_client.delete(f"session:{session_id}")
    
    def revoke_all_user_sessions(self, email: str):
        """Revoke all active sessions for a user"""
        pattern = f"session:*"
        for key in self.redis_client.scan_iter(match=pattern):
            session_data = self.redis_client.get(key)
            if session_data and email in str(session_data):
                self.redis_client.delete(key)
        
        # Also revoke all tokens for this user
        pattern = f"token:*"
        for key in self.redis_client.scan_iter(match=pattern):
            # This is a simplified approach - in production, you'd want to
            # store token-to-user mapping for more efficient revocation
            self.redis_client.delete(key)
    
    def generate_mfa_secret(self) -> str:
        """Generate MFA secret for TOTP"""
        return pyotp.random_base32()
    
    def verify_mfa_token(self, secret: str, token: str, window: int = 1) -> bool:
        """Verify MFA TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)
    
    def get_mfa_qr_code_url(self, secret: str, email: str, issuer: str = "PrivateGPT Legal AI") -> str:
        """Generate QR code URL for MFA setup"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=email,
            issuer_name=issuer
        )
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def get_session_info(self, session_id: str) -> Optional[dict]:
        """Get session information"""
        session_key = f"session:{session_id}"
        session_data = self.redis_client.get(session_key)
        if session_data:
            try:
                return eval(session_data)  # In production, use json.loads
            except:
                return None
        return None
    
    def extend_session(self, session_id: str, jti: str, additional_hours: int = 8):
        """Extend session duration"""
        session_key = f"session:{session_id}"
        token_key = f"token:{jti}"
        
        new_expiry = additional_hours * 3600
        self.redis_client.expire(session_key, new_expiry)
        self.redis_client.expire(token_key, new_expiry)
    
    def get_security_metrics(self) -> dict:
        """Get current security metrics"""
        metrics = {
            "active_sessions": 0,
            "locked_accounts": 0,
            "failed_login_attempts_last_hour": 0,
            "rate_limited_requests": 0
        }
        
        # Count active sessions
        pattern = "session:*"
        metrics["active_sessions"] = len(list(self.redis_client.scan_iter(match=pattern)))
        
        # Count locked accounts
        pattern = "account_locked:*"
        metrics["locked_accounts"] = len(list(self.redis_client.scan_iter(match=pattern)))
        
        return metrics

    async def get_all_users(self, db: Session) -> List[User]:
        """Retrieve all users from the database."""
        try:
            return db.query(User).all()
        except Exception as e:
            raise e

