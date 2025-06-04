"""
PrivateGPT Legal AI - Authentication Service
Database-backed authentication with advanced security features
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import secrets

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

# Import our modules
from models import User, LoginSession, AuditLog, SecurityMetric, get_db
from security import SecurityService
from utils import get_logger, log_security_event, log_audit_event

# Configure logging
logger = get_logger(__name__)

# Database session dependency
def get_db_session():
    """Get database session for dependency injection"""
    return get_db()

# Security service instance
security_service = SecurityService()

# Pydantic models for API
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12)
    role: str = "user"

class UserLogin(BaseModel):
    email: str
    password: str
    totp_code: Optional[str] = None

class UserResponse(BaseModel):
    email: str
    role: str
    active: bool
    created_at: datetime
    last_login: Optional[datetime]
    mfa_enabled: bool
    client_matters: List[str] = []

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)

class MFASetupResponse(BaseModel):
    secret: str
    qr_code_url: str
    backup_codes: List[str]

class MFAVerify(BaseModel):
    totp_code: str

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Auth Service...")
    
    # Initialize database tables
    from models import create_tables
    create_tables()
    
    logger.info("Auth Service startup complete")
    yield
    
    logger.info("Shutting down Auth Service...")
    logger.info("Auth Service shutdown complete")

# FastAPI app
app = FastAPI(
    title="PrivateGPT Legal AI - Authentication Service",
    description="Database-backed authentication with advanced security features",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# Dependency to get current user with security
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db_session)
) -> User:
    """Token validation with session tracking"""
    token = credentials.credentials
    
    try:
        # Verify token
        payload = security_service.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Get user from database
        with next(get_db()) as db:
            from models import get_user_by_email
            user = get_user_by_email(db, payload["sub"])
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            return user
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# Optional user dependency (for public endpoints that can benefit from user context)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db = Depends(get_db_session)
) -> Optional[User]:
    """Optional user authentication"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except:
        return None

# Health check endpoint
@app.get("/health")
async def health_check(db = Depends(get_db_session)):
    """Health check with security metrics"""
    try:
        # Test database connection
        from sqlalchemy import text
        with next(get_db()) as db:
            result = db.execute(text("SELECT 1"))
            db_status = "healthy" if result else "unhealthy"
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status,
            "service": "auth-service",
            "version": "1.0.0",
            "security_metrics": {
                "active_sessions": 0,
                "failed_logins_24h": 0,
                "rate_limited_requests": 0
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# Authentication endpoints
@app.post("/auth/login", response_model=TokenResponse)
async def login(
    user_login: UserLogin,
    request: Request,
    db = Depends(get_db_session)
):
    """Login with rate limiting and security monitoring"""
    client_ip = request.client.host
    
    # Rate limiting
    rate_check, _ = security_service.check_rate_limit(f"login:{client_ip}", 5, 5)  # 5 attempts per 5 minutes
    if not rate_check:
        await log_security_event(
            "rate_limit_exceeded",
            {"email": user_login.email, "ip": client_ip},
            db
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    try:
        # Get user from database
        with next(get_db()) as db:
            from models import get_user_by_email
            user = get_user_by_email(db, user_login.email)
            
            if not user or not security_service.verify_password(user_login.password, user.password_hash):
                await log_security_event(
                    "login_failed",
                    {"email": user_login.email, "ip": client_ip},
                    db
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            # Check if account is locked
            if user.is_account_locked():
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account is temporarily locked"
                )
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()
            
            # Create token
            token_data = security_service.create_access_token(
                {"email": user.email, "role": user.role, "client_matters": user.get_client_matters()},
                client_ip
            )
            
            await log_audit_event(
                user.email,
                "user_login",
                {"ip": client_ip},
                db
            )
            
            return TokenResponse(
                access_token=token_data["access_token"],
                token_type=token_data["token_type"],
                expires_in=token_data["expires_in"],
                user=UserResponse(
                    email=user.email,
                    role=user.role,
                    active=user.active,
                    created_at=user.created_at,
                    last_login=user.last_login,
                    mfa_enabled=user.mfa_enabled,
                    client_matters=user.get_client_matters()
                )
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

@app.post("/auth/register", response_model=UserResponse)
async def register(
    user_create: UserCreate,
    request: Request,
    db = Depends(get_db_session)
):
    """User registration with security validation"""
    client_ip = request.client.host
    
    # Rate limiting for registration
    rate_check, _ = security_service.check_rate_limit(f"register:{client_ip}", 3, 60)  # 3 per hour
    if not rate_check:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later."
        )
    
    try:
        # Check if user exists
        existing_user = await security_service.get_user_by_email(user_create.email, db)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate password strength
        if not security_service.validate_password_strength(user_create.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet security requirements"
            )
        
        # Create user
        user = await security_service.create_user(
            email=user_create.email,
            password=user_create.password,
            role=user_create.role,
            db=db
        )
        
        await log_audit_event(
            user.id,
            "user_registered",
            {"ip": client_ip},
            db
        )
        
        return UserResponse(
            email=user.email,
            role=user.role,
            active=user.active,
            created_at=user.created_at,
            last_login=user.last_login,
            mfa_enabled=user.mfa_enabled,
            client_matters=user.get_client_matters()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration service error"
        )

@app.post("/auth/verify")
async def verify_token(
    current_user: User = Depends(get_current_user)
):
    """Verify JWT token and return user info"""
    return {
        "valid": True,
        "user": UserResponse(
            email=current_user.email,
            role=current_user.role,
            active=current_user.active,
            created_at=current_user.created_at,
            last_login=current_user.last_login,
            mfa_enabled=current_user.mfa_enabled,
            client_matters=current_user.get_client_matters()
        )
    }

@app.post("/auth/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db_session)
):
    """Logout with session revocation"""
    try:
        token = credentials.credentials
        await security_service.revoke_session(token, db)
        
        await log_audit_event(
            current_user.id,
            "user_logout",
            {"ip": request.client.host},
            db
        )
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout service error"
        )

# User management endpoints
@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        email=current_user.email,
        role=current_user.role,
        active=current_user.active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        mfa_enabled=current_user.mfa_enabled,
        client_matters=current_user.get_client_matters()
    )

@app.post("/auth/change-password")
async def change_password(
    password_change: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db_session)
):
    """Change user password"""
    try:
        # Verify current password
        if not security_service.verify_password(password_change.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password
        if not security_service.validate_password_strength(password_change.new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password does not meet security requirements"
            )
        
        # Update password
        await security_service.update_user_password(
            current_user.id,
            password_change.new_password,
            db
        )
        
        await log_audit_event(
            current_user.id,
            "password_changed",
            {"ip": request.client.host},
            db
        )
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change service error"
        )

# MFA endpoints
@app.post("/auth/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db_session)
):
    """Setup MFA for user"""
    try:
        if current_user.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is already enabled"
            )
        
        # Generate TOTP secret and QR code
        secret = security_service.generate_mfa_secret()
        qr_code_url = security_service.get_mfa_qr_code_url(
            secret,
            current_user.email,
            "PrivateGPT Legal AI"
        )
        
        # Generate backup codes (placeholder since method doesn't exist)
        backup_codes = [secrets.token_hex(8) for _ in range(10)]
        
        # Store secret temporarily (user needs to verify before enabling)
        await security_service.store_temp_mfa_secret(
            current_user.id,
            secret,
            backup_codes,
            db
        )
        
        return MFASetupResponse(
            secret=secret,
            qr_code_url=qr_code_url,
            backup_codes=backup_codes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA setup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA setup service error"
        )

@app.post("/auth/mfa/verify")
async def verify_mfa_setup(
    mfa_verify: MFAVerify,
    request: Request,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db_session)
):
    """Verify and enable MFA"""
    try:
        # Verify TOTP code with temporary secret
        success = await security_service.verify_and_enable_mfa(
            current_user.id,
            mfa_verify.totp_code,
            db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid TOTP code"
            )
        
        await log_audit_event(
            current_user.id,
            "mfa_enabled",
            {"ip": request.client.host},
            db
        )
        
        return {"message": "MFA enabled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA verification service error"
        )

@app.post("/auth/mfa/disable")
async def disable_mfa(
    password_verify: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db_session)
):
    """Disable MFA (requires password confirmation)"""
    try:
        # Verify password
        if not security_service.verify_password(password_verify, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password verification failed"
            )
        
        # Disable MFA
        await security_service.disable_user_mfa(current_user.id, db)
        
        await log_audit_event(
            current_user.id,
            "mfa_disabled",
            {"ip": request.client.host},
            db
        )
        
        return {"message": "MFA disabled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA disable error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA disable service error"
        )

# Admin endpoints
@app.get("/auth/admin/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db_session)
):
    """List all users (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        users = await security_service.get_all_users(db)
        return [
            UserResponse(
                email=user.email,
                role=user.role,
                active=user.active,
                created_at=user.created_at,
                last_login=user.last_login,
                mfa_enabled=user.mfa_enabled,
                client_matters=user.get_client_matters()
            )
            for user in users
        ]
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User listing service error"
        )

@app.get("/auth/admin/security-metrics")
async def get_security_metrics(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db_session)
):
    """Get security metrics (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        metrics = await security_service.get_detailed_security_metrics(db)
        return metrics
    except Exception as e:
        logger.error(f"Security metrics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security metrics service error"
        )

if __name__ == "__main__":
    uvicorn.run(
        "auth_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 