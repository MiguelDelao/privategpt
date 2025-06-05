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
import uuid
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

# Import our modules
from models import User, LoginSession, AuditLog, SecurityMetric, get_db, Client, user_clients_association
from security import SecurityService
from utils import get_logger, log_security_event, log_audit_event

# Configure logging
logger = get_logger(__name__)

# Database session dependency
def get_db_session():
    """Get database session for dependency injection"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

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

class ClientResponse(BaseModel):
    id: str # UUID string
    created_at: datetime
    name: str

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    email: EmailStr
    role: str
    active: bool
    created_at: datetime
    last_login: Optional[datetime]
    mfa_enabled: bool
    authorized_clients: List[ClientResponse] = []

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

    class Config:
        from_attributes = True

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
    title="Authentication Service",
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
    db: Session = Depends(get_db_session)
):
    """Login with rate limiting and security monitoring"""
    client_ip = request.client.host
    
    # Rate limiting
    rate_check, _ = security_service.check_rate_limit(f"login:{client_ip}", 20, 5)  # 20 attempts per 5 minutes
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
            
            # Ensure authorized_clients are loaded if lazy='selectin' wasn't enough or for explicit refresh
            # This might not be strictly necessary with lazy='selectin' but can ensure data freshness
            # db.refresh(user, attribute_names=['authorized_clients']) # Optional: refresh if needed

            client_ids_for_token = [client.id for client in user.authorized_clients]
            
            token_data = security_service.create_access_token(
                {"email": user.email, "role": user.role, "authorized_client_ids": client_ids_for_token},
                client_ip
            )
            
            await log_audit_event(
                user.email,
                "user_login",
                {"ip": client_ip},
                db
            )
            
            # Construct UserResponse for the token
            # This now leverages from_attributes in UserResponse Pydantic model
            user_response_data = UserResponse.model_validate(user)

            return TokenResponse(
                access_token=token_data["access_token"],
                token_type=token_data["token_type"],
                expires_in=token_data["expires_in"],
                user=user_response_data
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
        
        return UserResponse.model_validate(user)
        
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
        "user": UserResponse.model_validate(current_user)
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
async def get_current_user_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db_session)):
    """Get current user information"""
    # Eager load/refresh authorized_clients if necessary for the response model
    # db.refresh(current_user, attribute_names=['authorized_clients']) # This might be redundant with lazy='selectin'
    return UserResponse.model_validate(current_user) # Uses from_attributes and relationship loading

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
@app.get("/auth/admin/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """List all users (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        users = db.query(User).options(joinedload(User.authorized_clients)).all() # Eager load clients
        return [UserResponse.model_validate(user) for user in users]
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

# --- New Pydantic Models for Client Management ---
class ClientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class ClientCreate(ClientBase):
    pass

class UserClientAssociationRequest(BaseModel):
    client_ids: List[str] # List of Client UUID strings

# --- NEW: Global Client Management Endpoints (Admin Only) ---

@app.post("/admin/clients/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_global_client(
    client_create: ClientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new global client"""
    ensure_admin(current_user)
    existing_client = db.query(Client).filter(Client.name == client_create.name).first()
    if existing_client:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client name already exists")
    
    new_client = Client(name=client_create.name, created_by_email=current_user.email)
    db.add(new_client)
    try:
        db.commit()
        db.refresh(new_client)
    except IntegrityError: # Catch potential race conditions or other DB errors
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create client due to a database error")
    return ClientResponse.model_validate(new_client)

@app.get("/admin/clients/", response_model=List[ClientResponse])
async def list_global_clients(
    current_user: User = Depends(get_current_user), # Still require auth, but admin check is not strictly needed for list
    db: Session = Depends(get_db_session)
):
    """List all global clients"""
    # ensure_admin(current_user) # Optional: make listing clients admin-only too
    clients = db.query(Client).order_by(Client.name).all()
    return [ClientResponse.model_validate(client) for client in clients]

@app.delete("/admin/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_global_client(
    client_id: str, # Should be UUID string
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete a global client"""
    ensure_admin(current_user)
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    
    # Optional: Check if client is associated with any users before deleting, or handle cascade if DB supports it.
    # For now, direct delete. If user_clients_association has FK constraints, this might fail if client is in use.
    # Consider adding a check: if client.authorized_users: raise HTTPException(detail="Client is in use")

    db.delete(client)
    try:
        db.commit()
    except IntegrityError: # e.g. if FK constraint prevents deletion because it's linked
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Client {client.name} cannot be deleted, possibly in use or other database constraint.")
    return Response(status_code=status.HTTP_204_NO_CONTENT) # FastAPI expects Response for 204

# --- NEW: User-Client Association Endpoints (Admin Only) ---

@app.get("/admin/users/{user_email}/clients", response_model=List[ClientResponse])
async def get_clients_for_user(
    user_email: EmailStr,
    current_admin_user: User = Depends(get_current_user), # current_user is admin
    db: Session = Depends(get_db_session)
):
    """Get clients for a specific user"""
    ensure_admin(current_admin_user)
    target_user = db.query(User).options(joinedload(User.authorized_clients)).filter(User.email == user_email).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")
    return [ClientResponse.model_validate(client) for client in target_user.authorized_clients]

@app.put("/admin/users/{user_email}/clients", response_model=UserResponse) # Returns the updated user
async def update_clients_for_user(
    user_email: EmailStr,
    association_request: UserClientAssociationRequest,
    current_admin_user: User = Depends(get_current_user), # current_user is admin
    db: Session = Depends(get_db_session)
):
    """Update clients for a specific user"""
    ensure_admin(current_admin_user)
    target_user = db.query(User).filter(User.email == user_email).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    # Validate all incoming client_ids exist
    clients_to_associate = []
    if association_request.client_ids:
        clients_to_associate = db.query(Client).filter(Client.id.in_(association_request.client_ids)).all()
        if len(clients_to_associate) != len(set(association_request.client_ids)):
            # Find which IDs were not found for a more detailed error (optional)
            found_ids = {client.id for client in clients_to_associate}
            missing_ids = [cid for cid in association_request.client_ids if cid not in found_ids]
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"One or more client IDs not found: {missing_ids}")

    target_user.authorized_clients = clients_to_associate # Replace existing associations
    
    db.add(target_user) # Add user to session to track changes to relationship
    try:
        db.commit()
        db.refresh(target_user) # Refresh to get updated state, especially relationships
        # Ensure relationships are loaded for the response model
        # db.refresh(target_user, attribute_names=['authorized_clients']) # Re-evaluate if needed based on lazy loading config
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update client associations due to a database error")

    return UserResponse.model_validate(target_user)

# --- Helper function for admin check ---
def ensure_admin(current_user: User):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted: Requires admin privileges"
        )

if __name__ == "__main__":
    uvicorn.run(
        "auth_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 