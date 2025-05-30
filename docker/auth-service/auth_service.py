"""
PrivateGPT Legal AI - Authentication Service
JWT-based authentication with comprehensive audit logging for legal compliance
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
import structlog

from utils import AuditLogger, SecurityMetrics

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "8"))
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))

# Initialize logging
logger = structlog.get_logger()
audit_logger = AuditLogger()
security_metrics = SecurityMetrics()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FastAPI app
app = FastAPI(
    title="PrivateGPT Legal AI - Authentication Service",
    description="JWT Authentication with Legal Compliance",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Data models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "user"
    client_matters: list[str] = []

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None
    client_matters: Optional[list[str]] = None
    active: Optional[bool] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_role: str

# User storage (file-based for MVP)
USER_DATA_FILE = Path("/app/data/users.json")

def load_users() -> Dict[str, Any]:
    """Load users from JSON file"""
    if USER_DATA_FILE.exists():
        try:
            with open(USER_DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load users", error=str(e))
            return {}
    return {}

def save_users(users: Dict[str, Any]) -> None:
    """Save users to JSON file"""
    try:
        USER_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        logger.error("Failed to save users", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to save user data")

def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Validate JWT token and return user info"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        users = load_users()
        if email not in users:
            raise HTTPException(status_code=401, detail="User not found")
        
        user = users[email]
        if not user.get("active", True):
            raise HTTPException(status_code=401, detail="User account disabled")
        
        return {"email": email, **user}
    
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth-service", "timestamp": datetime.utcnow()}

@app.post("/auth/login", response_model=TokenResponse)
async def login(user_login: UserLogin):
    """Authenticate user and return JWT token"""
    request_id = str(uuid.uuid4())
    
    try:
        users = load_users()
        
        # Check if user exists
        if user_login.email not in users:
            audit_logger.log_auth_event(
                event_type="login_failed",
                user_email=user_login.email,
                reason="user_not_found",
                request_id=request_id
            )
            security_metrics.increment_failed_login(user_login.email)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = users[user_login.email]
        
        # Check if account is active
        if not user.get("active", True):
            audit_logger.log_auth_event(
                event_type="login_failed",
                user_email=user_login.email,
                reason="account_disabled",
                request_id=request_id
            )
            raise HTTPException(status_code=401, detail="Account disabled")
        
        # Verify password
        if not verify_password(user_login.password, user["password_hash"]):
            audit_logger.log_auth_event(
                event_type="login_failed",
                user_email=user_login.email,
                reason="invalid_password",
                request_id=request_id
            )
            security_metrics.increment_failed_login(user_login.email)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create JWT token
        token_data = {
            "sub": user_login.email,
            "role": user["role"],
            "client_matters": user.get("client_matters", [])
        }
        access_token = create_access_token(token_data)
        
        # Log successful login
        audit_logger.log_auth_event(
            event_type="login_success",
            user_email=user_login.email,
            user_role=user["role"],
            request_id=request_id
        )
        
        security_metrics.increment_successful_login(user_login.email)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=JWT_EXPIRY_HOURS * 3600,
            user_role=user["role"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error", error=str(e), request_id=request_id)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/auth/verify")
async def verify_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Verify JWT token and return user info"""
    return {
        "valid": True,
        "user": {
            "email": current_user["email"],
            "role": current_user["role"],
            "client_matters": current_user.get("client_matters", [])
        }
    }

@app.post("/auth/create-user")
async def create_user(
    user_create: UserCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create new user (admin only)"""
    request_id = str(uuid.uuid4())
    
    # Check admin permission
    if current_user["role"] != "admin":
        audit_logger.log_auth_event(
            event_type="unauthorized_action",
            user_email=current_user["email"],
            action="create_user",
            reason="insufficient_permissions",
            request_id=request_id
        )
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    try:
        users = load_users()
        
        # Check if user already exists
        if user_create.email in users:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Create user
        user_data = {
            "password_hash": hash_password(user_create.password),
            "role": user_create.role,
            "client_matters": user_create.client_matters,
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": current_user["email"]
        }
        
        users[user_create.email] = user_data
        save_users(users)
        
        # Log user creation
        audit_logger.log_auth_event(
            event_type="user_created",
            user_email=user_create.email,
            created_by=current_user["email"],
            user_role=user_create.role,
            request_id=request_id
        )
        
        return {"message": "User created successfully", "email": user_create.email}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User creation error", error=str(e), request_id=request_id)
        raise HTTPException(status_code=500, detail="Failed to create user")

@app.put("/auth/update-user/{user_email}")
async def update_user(
    user_email: str,
    user_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user (admin only or self)"""
    request_id = str(uuid.uuid4())
    
    # Check permissions
    if current_user["role"] != "admin" and current_user["email"] != user_email:
        audit_logger.log_auth_event(
            event_type="unauthorized_action",
            user_email=current_user["email"],
            action="update_user",
            target_user=user_email,
            reason="insufficient_permissions",
            request_id=request_id
        )
        raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        users = load_users()
        
        if user_email not in users:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user data
        if user_update.password:
            users[user_email]["password_hash"] = hash_password(user_update.password)
        
        if user_update.role and current_user["role"] == "admin":
            users[user_email]["role"] = user_update.role
        
        if user_update.client_matters is not None:
            users[user_email]["client_matters"] = user_update.client_matters
        
        if user_update.active is not None and current_user["role"] == "admin":
            users[user_email]["active"] = user_update.active
        
        users[user_email]["updated_at"] = datetime.utcnow().isoformat()
        users[user_email]["updated_by"] = current_user["email"]
        
        save_users(users)
        
        # Log user update
        audit_logger.log_auth_event(
            event_type="user_updated",
            user_email=user_email,
            updated_by=current_user["email"],
            request_id=request_id
        )
        
        return {"message": "User updated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User update error", error=str(e), request_id=request_id)
        raise HTTPException(status_code=500, detail="Failed to update user")

@app.get("/auth/users")
async def list_users(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all users (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    users = load_users()
    user_list = []
    
    for email, user_data in users.items():
        user_list.append({
            "email": email,
            "role": user_data["role"],
            "active": user_data.get("active", True),
            "client_matters": user_data.get("client_matters", []),
            "created_at": user_data.get("created_at"),
            "last_updated": user_data.get("updated_at")
        })
    
    return {"users": user_list}

# Initialize default admin user if no users exist
def initialize_default_admin():
    """Create default admin user if no users exist"""
    users = load_users()
    if not users:
        default_admin = {
            "password_hash": hash_password("admin123"),
            "role": "admin",
            "client_matters": [],
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": "system"
        }
        users["admin@legal-ai.local"] = default_admin
        save_users(users)
        logger.info("Default admin user created", email="admin@legal-ai.local")

if __name__ == "__main__":
    # Initialize default admin
    initialize_default_admin()
    
    # Start the server
    uvicorn.run(
        "auth_service:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    ) 