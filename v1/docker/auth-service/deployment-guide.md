# 🚀 **Auth Service Deployment Guide**

Complete deployment guide for the database-backed authentication service with PostgreSQL, Redis, and advanced security features.

## 📋 **Prerequisites**

- Docker & Docker Compose installed
- PostgreSQL 16+ (provided via Docker)
- Redis 7+ (provided via Docker)
- 2GB+ RAM available
- SSL certificates (for production)

## 🚀 **Quick Start**

### 1. **Start Database Services**
```bash
# Start PostgreSQL and Redis first
docker-compose -f docker-compose.auth.yml up -d auth-postgres redis

# Verify services are healthy
docker-compose -f docker-compose.auth.yml ps
```

### 2. **Start Auth Service**
```bash
# Build and start the auth service
docker-compose -f docker-compose.auth.yml up --build auth-service
```

### 3. **Integration with Main Stack**

Update other services to use the auth endpoints:

**Streamlit App Environment:**
```yaml
environment:
  - AUTH_SERVICE_URL=http://auth-service:8000
```

**Knowledge Service Environment:**
```yaml
environment:
  - AUTH_SERVICE_URL=http://auth-service:8000
```

## 🔧 **Configuration**

### Environment Variables

Create `.env` file in your project root:

```bash
# Database Configuration
POSTGRES_PASSWORD=your_secure_postgres_password_here
REDIS_PASSWORD=your_secure_redis_password_here

# Auth Service Configuration  
AUTH_SECRET_KEY=your-super-secret-jwt-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=30

# Security Configuration
ENVIRONMENT=production
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
PASSWORD_MIN_LENGTH=12
MFA_ISSUER=PrivateGPT Legal AI

# Optional: Admin User
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_EMAIL=admin@yourdomain.com
DEFAULT_ADMIN_PASSWORD=change_this_secure_password
```

### Production Deployment

For production environments:

```bash
# Use production profile with optimized settings
docker-compose -f docker-compose.auth.yml --profile production up -d
```

**Production Environment Variables:**
```bash
# Strong secrets (use proper secret management)
AUTH_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)

# Production security settings
ENVIRONMENT=production
LOG_LEVEL=WARNING
RATE_LIMIT_REQUESTS=50
RATE_LIMIT_WINDOW=3600
PASSWORD_MIN_LENGTH=14

# SSL/TLS Configuration
SSL_CERT_PATH=/certs/cert.pem
SSL_KEY_PATH=/certs/key.pem
```

## 🔐 **Security Features**

### Password Policy
- Minimum 12 characters (configurable)
- Must contain uppercase, lowercase, numbers, and symbols
- Password history tracking (prevents reuse)
- Secure bcrypt hashing with salt

### Rate Limiting
- Login attempts: 5 per 5 minutes per IP
- Registration: 3 per hour per IP
- API calls: 100 per hour per user
- Automatic IP blocking for abuse

### Multi-Factor Authentication (MFA)
- TOTP-based (Google Authenticator, Authy compatible)
- Backup codes for recovery
- QR code generation for easy setup
- Optional enforcement for admin users

### Session Management
- JWT tokens with session tracking
- Refresh token rotation
- Session revocation on logout
- Automatic cleanup of expired sessions

### Audit Logging
- All authentication events logged
- ELK Stack integration for analysis
- Legal compliance (7-year retention)
- Real-time security monitoring

## 📊 **Monitoring & Logging**

### Health Checks
```bash
# Check service health
curl http://localhost:8001/health

# Expected response:
{
  "status": "healthy",
  "database": "healthy", 
  "security_metrics": {
    "active_sessions": 5,
    "failed_logins_24h": 2,
    "rate_limited_ips": 0
  }
}
```

### Log Analysis
```bash
# View auth service logs
docker-compose logs -f auth-service

# Search for security events
docker-compose logs auth-service | grep "security_event"

# Monitor failed logins
docker-compose logs auth-service | grep "login_failed"
```

### ELK Stack Integration

The service automatically sends structured logs to ELK Stack:

```json
{
  "@timestamp": "2024-01-15T10:30:00.000Z",
  "service": "auth-service",
  "level": "INFO",
  "event_type": "login_success",
  "user_id": 123,
  "ip_address": "192.168.1.100",
  "session_id": "sess_abc123",
  "compliance": {
    "retention_years": 7,
    "data_classification": "sensitive"
  }
}
```

## 🔧 **API Endpoints**

### Authentication
- `POST /auth/login` - User login with MFA support
- `POST /auth/register` - User registration
- `POST /auth/logout` - Session termination
- `POST /auth/verify` - Token validation

### User Management
- `GET /auth/me` - Current user info
- `POST /auth/change-password` - Password update
- `POST /auth/mfa/setup` - MFA configuration
- `POST /auth/mfa/verify` - MFA activation

### Admin Endpoints
- `GET /auth/admin/users` - List all users
- `GET /auth/admin/security-metrics` - Security dashboard data
- `POST /auth/admin/users/{id}/disable` - Disable user account

## 🚨 **Troubleshooting**

### Common Issues

**Database Connection Failed:**
```bash
# Check PostgreSQL status
docker-compose logs auth-postgres

# Verify connection
docker-compose exec auth-postgres psql -U privategpt -d privategpt_auth -c "SELECT 1;"
```

**Redis Connection Failed:**
```bash
# Check Redis status  
docker-compose logs auth-redis

# Test connection
docker-compose exec auth-redis redis-cli ping
```

**Migration Issues:**
```bash
# Check migration logs
docker-compose logs auth-service | grep "migration"

# Manual migration trigger
docker-compose exec auth-service python -c "from migrate_data import migrate_json_to_db; import asyncio; asyncio.run(migrate_json_to_db())"
```

### Performance Tuning

**Database Optimization:**
```sql
-- Add indexes for better performance
CREATE INDEX CONCURRENTLY idx_users_username ON users(username);
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY idx_login_sessions_user_id ON login_sessions(user_id);
CREATE INDEX CONCURRENTLY idx_audit_logs_user_id_timestamp ON audit_logs(user_id, timestamp);
```

**Redis Configuration:**
```bash
# Optimize Redis for session storage
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET maxmemory 512mb
```

## 🔄 **Data Migration**

### Automatic Migration

The auth service automatically detects and migrates existing JSON user data:

1. **Backup Creation**: Automatic backup of `users.json` to `users.json.backup`
2. **Data Validation**: Validates existing user data structure
3. **Secure Migration**: Preserves password hashes and user settings
4. **Verification**: Confirms successful migration with integrity checks

### Manual Migration

If automatic migration fails:

1. Stop the auth service
```bash
docker-compose stop auth-service
```

2. Run manual migration
```bash
docker-compose exec auth-service python migrate_data.py
```

3. Verify migration
```bash
docker-compose exec auth-postgres psql -U privategpt -d privategpt_auth -c "SELECT COUNT(*) FROM users;"
```

4. Restart service
```bash
docker-compose start auth-service
```

## 📈 **Scaling & High Availability**

### Load Balancing
```yaml
# docker-compose.yml
auth-service:
  deploy:
    replicas: 3
  depends_on:
    - auth-postgres
    - auth-redis
```

### Database Clustering
```yaml
# PostgreSQL primary-replica setup
auth-postgres-primary:
  image: postgres:16-alpine
  environment:
    POSTGRES_REPLICATION_MODE: master
    
auth-postgres-replica:
  image: postgres:16-alpine  
  environment:
    POSTGRES_REPLICATION_MODE: slave
    POSTGRES_MASTER_SERVICE: auth-postgres-primary
```

### Redis Clustering
```yaml
# Redis Sentinel for high availability
redis-sentinel:
  image: redis:7-alpine
  command: redis-sentinel /etc/redis/sentinel.conf
```

## 🔒 **Security Hardening**

### Container Security
```dockerfile
# Run as non-root user
USER 1000:1000

# Read-only filesystem
--read-only --tmpfs /tmp

# Drop capabilities
--cap-drop=ALL --cap-add=NET_BIND_SERVICE
```

### Network Security
```yaml
# Isolated network
networks:
  auth-network:
    driver: bridge
    internal: true
```

### Secrets Management
```bash
# Use Docker secrets in production
echo "super_secret_key" | docker secret create auth_secret_key -
```

## 📝 **Compliance & Legal**

### GDPR Compliance
- User data encryption at rest and in transit
- Right to be forgotten (user deletion)
- Data export capabilities
- Audit trail for all data access

### Legal Requirements
- 7-year audit log retention
- Secure password storage (bcrypt)
- Session timeout enforcement
- Failed login attempt monitoring

---

## 🎯 **Next Steps**

1. **Test the deployment** with the provided health checks
2. **Configure monitoring** with ELK Stack integration  
3. **Set up backup procedures** for PostgreSQL data
4. **Implement SSL/TLS** for production environments
5. **Configure log rotation** and retention policies

For additional support, check the logs and monitoring dashboards, or refer to the troubleshooting section above. 