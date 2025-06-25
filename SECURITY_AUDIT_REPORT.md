# Security Audit Report - PrivateGPT Codebase

**Date**: 2025-06-24  
**Auditor**: Security Analysis

## Executive Summary

This security audit identified several critical vulnerabilities in the PrivateGPT codebase that require immediate attention. The most serious issues include exposed debug endpoints without authentication, hardcoded credentials, and authentication bypass configurations.

## Critical Findings

### 1. Exposed Debug Endpoints Without Authentication (CRITICAL)

**Location**: `/src/privategpt/services/gateway/api/chat_router.py`

Multiple debug endpoints are exposed without any authentication requirements:

- `/api/chat/debug/simple` (line 1008)
- `/api/chat/debug/stream-test` (line 1013)
- `/api/chat/debug/simple-test/{token}` (line 1081)
- `/api/chat/debug/stream-session/{stream_token}` (line 1087)
- `/api/chat/debug/session` (line 1117)
- `/api/chat/debug/conversations` (line 1136) - **Exposes all conversations**
- `/api/chat/debug/create-conversation` (line 1158)
- `/api/chat/debug/test-conversation` (line 1470)

**Risk**: These endpoints allow unauthenticated access to:
- View all conversations in the database
- Create new conversations
- Access streaming sessions
- Execute arbitrary chat requests

**Recommendation**: Remove all debug endpoints or protect them with authentication and restrict to development environments only.

### 2. Authentication Bypass in Middleware Configuration (CRITICAL)

**Location**: `/src/privategpt/services/gateway/main.py` (lines 141-148)

The authentication middleware explicitly excludes critical paths:
```python
excluded_paths=[
    "/api/test/",  # All test endpoints bypass auth
    "/api/chat/debug/",  # Debug endpoints bypass auth
    ...
]
```

**Risk**: Any endpoint under these paths can be accessed without authentication.

**Recommendation**: Remove these exclusions in production environments.

### 3. Test Endpoint Without Authentication (HIGH)

**Location**: `/src/privategpt/services/gateway/api/gateway_router.py` (lines 28-36)

```python
@router.get("/test/auth-check")
async def test_auth_check(request: Request):
    """Test endpoint to check authentication state."""
    user = getattr(request.state, 'user', None)
    return {
        "has_user": user is not None,
        "user": user,
        "path": request.url.path
    }
```

**Risk**: Exposes internal authentication state and user information.

**Recommendation**: Remove or protect this endpoint.

### 4. Hardcoded Credentials (HIGH)

Multiple locations contain hardcoded credentials:

#### a. Configuration Files
- **`config.json`** (lines 31-34):
  ```json
  "default_admin_email": "admin@admin.com",
  "default_admin_password": "admin",
  ```

- **`.env`** (lines 8-14, 17-22):
  ```
  JWT_SECRET_KEY=admin123456789abcdef
  DEFAULT_ADMIN_PASSWORD=admin
  WEAVIATE_API_KEY=admin
  N8N_PASSWORD=admin
  ```

- **`docker-compose.yml`**:
  - PostgreSQL: `POSTGRES_PASSWORD: secret` (line 20)
  - Keycloak DB: `POSTGRES_PASSWORD: keycloak_secret` (line 30)
  - Keycloak Admin: `KEYCLOAK_ADMIN_PASSWORD: admin123` (line 56)

#### b. Database Configuration
- **`config.json`** (line 4):
  ```json
  "database_url": "postgresql://privategpt:secret@db:5432/privategpt"
  ```

**Risk**: Default credentials are well-known and easily exploitable.

**Recommendation**: 
- Use environment variables for all credentials
- Generate strong, unique passwords for production
- Never commit credentials to version control

### 5. Demo User Auto-Creation with Admin Privileges (HIGH)

**Location**: `/src/privategpt/services/gateway/api/chat_router.py` (lines 42-68)

When authentication is disabled or invalid, the system creates a demo user with admin privileges:
```python
demo_user = User(
    id=1,
    keycloak_id="demo-user",
    email="admin@admin.com",
    username="admin",
    role="admin",  # Admin role granted!
    ...
)
```

**Risk**: Bypasses authentication and grants admin access.

**Recommendation**: Remove demo user creation or restrict to development environments only.

### 6. Weak JWT Secret Key (MEDIUM)

**Location**: `/src/privategpt/shared/security.py` (line 34)

```python
_SECRET_KEY: str = settings.get("security.jwt.secret_key") or os.getenv("JWT_SECRET_KEY", "change_me")
```

**Risk**: Fallback to weak default "change_me" if not configured.

**Recommendation**: Require strong JWT secret key configuration on startup.

### 7. SQL Injection Protection (LOW - Properly Handled)

**Positive Finding**: The codebase properly uses SQLAlchemy ORM with parameterized queries. No raw SQL execution or string concatenation vulnerabilities were found.

### 8. Input Validation (MEDIUM)

Most API endpoints use Pydantic models for input validation, which is good. However, some endpoints accept unvalidated input:

- Chat endpoints that directly pass user content to LLMs
- File path parameters in some debug endpoints

**Recommendation**: Implement comprehensive input validation for all user inputs.

## Additional Security Concerns

### 1. CORS Configuration Too Permissive

**Location**: `/src/privategpt/services/gateway/main.py` (lines 113-125)

The CORS configuration includes `"null"` origin which can be exploited.

### 2. Error Information Disclosure

Debug endpoints return full stack traces and internal error details that could aid attackers.

### 3. No Rate Limiting

No rate limiting is implemented on authentication endpoints, allowing brute force attacks.

## Recommendations Summary

1. **IMMEDIATE ACTIONS**:
   - Remove or secure all debug endpoints
   - Remove authentication bypass configurations
   - Change all default passwords and credentials
   - Remove demo user auto-creation

2. **SHORT TERM**:
   - Implement proper environment-based configuration
   - Add rate limiting to authentication endpoints
   - Restrict CORS origins
   - Add security headers (CSP, X-Frame-Options, etc.)

3. **LONG TERM**:
   - Implement API key rotation
   - Add audit logging for security events
   - Implement principle of least privilege for all services
   - Regular security audits and penetration testing

## Conclusion

The codebase has several critical security vulnerabilities that must be addressed before production deployment. The most serious issues are the exposed debug endpoints and hardcoded credentials. While the application uses modern security practices in some areas (SQLAlchemy ORM, Pydantic validation), the debug features and default configurations create significant security risks.