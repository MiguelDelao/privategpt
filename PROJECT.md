# PrivateGPT - Enterprise-Grade RAG System

## Overview
PrivateGPT is a production-ready Retrieval-Augmented Generation (RAG) system built with microservices architecture, designed for enterprise deployment with comprehensive authentication, document management, and AI-powered chat capabilities.

## Architecture

### System Design
- **Pattern**: Domain-Driven Design (DDD) with Vertical Slice Architecture
- **Deployment**: Docker Compose orchestration with service isolation
- **Communication**: HTTP/REST APIs with centralized gateway routing
- **Authentication**: Keycloak OIDC/OAuth2 with JWT token validation
- **Data Flow**: API Gateway → Microservices → Vector Store/Database

### Core Services

#### 1. API Gateway (`gateway-service`)
**Purpose**: Centralized routing, authentication, and request proxying
- **Location**: `src/privategpt/services/gateway/`
- **Port**: 8000
- **Responsibilities**:
  - JWT token validation via Keycloak integration
  - Request authentication middleware
  - Service discovery and load balancing
  - CORS and security headers management
  - User session management

**Key Components**:
- `main.py`: FastAPI application with middleware stack
- `api/gateway_router.py`: Authentication endpoints and service proxying
- `core/keycloak_auth.py`: Keycloak OIDC password grant flow
- `core/proxy.py`: HTTP request proxying to backend services

#### 2. RAG Service (`rag-service`)
**Purpose**: Document processing, embedding, and retrieval
- **Location**: `src/privategpt/services/rag/`
- **Port**: 8001
- **Responsibilities**:
  - Document ingestion and chunking
  - Vector embedding generation
  - Semantic search and retrieval
  - Context-aware response generation

#### 3. LLM Service (`llm-service`)
**Purpose**: Language model inference and generation
- **Location**: `src/privategpt/services/llm/`
- **Port**: 8002
- **Responsibilities**:
  - Text generation and completion
  - Chat conversation management
  - Model parameter configuration
  - Response streaming

#### 4. UI Service (`ui-service`)
**Purpose**: Streamlit-based web interface
- **Location**: `src/privategpt/services/ui/`
- **Port**: 8501
- **Responsibilities**:
  - User authentication interface
  - Document upload and management
  - Chat interface with RAG capabilities
  - Admin panel for system management

### Infrastructure Services

#### Authentication (Keycloak)
- **Service**: `keycloak`
- **Port**: 8080
- **Database**: PostgreSQL (`keycloak-db`)
- **Configuration**: Automated realm setup via `scripts/init-keycloak-realm.sh`
- **Features**:
  - OIDC/OAuth2 provider
  - User management and roles
  - JWT token issuance
  - Admin console at `http://localhost:8080`

#### Databases
- **Main Database**: PostgreSQL (`db`) - Application data
- **Keycloak Database**: PostgreSQL (`keycloak-db`) - Identity management
- **Vector Store**: Weaviate - Document embeddings and search
- **Cache**: Redis - Session storage and caching

#### Observability
- **Message Queue**: Celery with Redis backend
- **Monitoring**: Health check endpoints across all services
- **Logging**: Structured JSON logging with correlation IDs

## Data Models

### Core Domain Entities

#### Document (`src/privategpt/core/domain/document.py`)
```python
class Document:
    doc_id: UUID
    user_id: str
    title: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

#### Chunk (`src/privategpt/core/domain/chunk.py`)
```python
class Chunk:
    chunk_id: UUID
    document_id: UUID
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    position: int
```

#### User (Keycloak-managed)
- **ID**: UUID from Keycloak
- **Roles**: `admin`, `user`
- **Attributes**: email, name, preferences
- **Authentication**: JWT tokens with 1-hour expiry

### Database Schema (`src/privategpt/infra/database/models.py`)
- **SQLAlchemy 2.0** with async support
- **Alembic migrations** for schema versioning
- **Connection pooling** with PostgreSQL
- **Relationship mapping** between entities

## Authentication Flow

### JWT Token Validation
1. **Login**: UI calls `/api/auth/login` with credentials
2. **Keycloak Exchange**: Gateway exchanges credentials for JWT via password grant
3. **Token Storage**: UI stores access_token in session state
4. **Request Authentication**: Middleware validates JWT on protected endpoints
5. **JWKS Validation**: Signature verification using Keycloak's public keys

### Security Implementation
- **Middleware**: `KeycloakAuthMiddleware` for request interception
- **Token Validation**: JWKS-based signature verification
- **Role Extraction**: Claims parsing for authorization
- **Session Management**: Refresh token support for long sessions

## Development Workflow

### Build System
```bash
# Clean build (removes containers and volumes)
make clean

# Full build with automated setup
make build

# Development mode with hot reloading
make dev

# Service-specific operations
make logs service=gateway-service
make restart service=ui-service
```

### Service Dependencies
1. **Base Image**: `docker/base/Dockerfile` - Common Python dependencies
2. **Service Images**: Inherit from base for fast builds
3. **Health Checks**: All services implement `/health` endpoints
4. **Startup Order**: Database → Keycloak → Application Services

### Configuration Management
- **Settings**: `src/privategpt/shared/settings.py` - Pydantic-based configuration
- **Environment Variables**: Docker Compose `.env` support
- **Service Discovery**: Internal Docker networking
- **Secrets**: Keycloak client secrets, database credentials

## API Documentation

### Gateway Endpoints
```
POST /api/auth/login          # User authentication
POST /api/auth/verify         # Token validation
GET  /api/auth/me            # Current user profile
GET  /api/auth/keycloak/config # Frontend Keycloak config

# Proxied service endpoints
/api/rag/*                   # RAG service operations
/api/llm/*                   # LLM service operations
/api/admin/*                 # Administrative functions
```

### Service Communication
- **Internal**: HTTP with service hostnames (`http://rag-service:8001`)
- **External**: Gateway exposure on `localhost:8000`
- **Authentication**: Bearer token propagation
- **Error Handling**: Standardized HTTP status codes

## Deployment Configuration

### Docker Compose Services
```yaml
services:
  gateway-service:     # API Gateway
  rag-service:         # RAG processing
  llm-service:         # Language model
  ui-service:          # Web interface
  keycloak:            # Identity provider
  keycloak-db:         # Keycloak database
  db:                  # Application database
  redis:               # Cache and queues
  weaviate:            # Vector database
```

### Network Configuration
- **Internal Network**: `privategpt_default`
- **Port Mapping**: Host ports mapped to service ports
- **Health Checks**: Container health monitoring
- **Dependencies**: Service startup ordering

## Key Technical Decisions

### Architecture Patterns
- **Vertical Slices**: Feature-complete service boundaries
- **Ports & Adapters**: Clean dependency inversion
- **Repository Pattern**: Data access abstraction
- **Factory Pattern**: Service instantiation

### Technology Stack
- **Backend**: FastAPI + SQLAlchemy 2.0 + Pydantic
- **Frontend**: Streamlit with custom authentication
- **Identity**: Keycloak for enterprise SSO integration
- **Vector Search**: Weaviate for semantic similarity
- **Embeddings**: Sentence Transformers (BGE models)
- **LLM Integration**: Ollama-compatible API

### Performance Optimizations
- **Async I/O**: All database and HTTP operations
- **Connection Pooling**: Database and HTTP client reuse
- **Caching**: Redis for session and computation caching
- **Batch Processing**: Celery for background tasks

## Troubleshooting

### Common Issues
1. **Authentication Failures**: Check Keycloak realm configuration
2. **Service Connectivity**: Verify Docker network and health checks
3. **Database Migrations**: Ensure schema is up to date
4. **Port Conflicts**: Check for conflicting services on host ports

### Debugging Commands
```bash
# Service logs
docker-compose logs -f gateway-service

# Database access
docker-compose exec db psql -U privategpt -d privategpt

# Keycloak admin
# URL: http://localhost:8080
# Credentials: admin/admin123

# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/status
```

### Configuration Validation
- **Environment**: Check `.env` file and environment variables
- **Keycloak**: Verify realm, client, and user configuration
- **Database**: Confirm connection strings and credentials
- **Services**: Validate service discovery and routing

## Development Guidelines

### Code Organization
- **Domain Layer**: Business logic and entities
- **Infrastructure Layer**: External integrations
- **Application Layer**: Service coordination
- **Shared Modules**: Cross-cutting concerns

### Testing Strategy
- **Unit Tests**: Domain logic testing
- **Integration Tests**: Service interaction testing
- **End-to-End Tests**: Full workflow validation
- **Authentication Tests**: Token validation flows

### Security Considerations
- **Input Validation**: Pydantic models for data validation
- **SQL Injection**: Parameterized queries via SQLAlchemy
- **XSS Protection**: Content Security Policy headers
- **CSRF Protection**: Token-based authentication
- **Data Encryption**: TLS for all external communication

This system provides a robust foundation for enterprise RAG applications with comprehensive authentication, scalable microservices architecture, and production-ready deployment capabilities.