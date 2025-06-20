# PrivateGPT - Enterprise-Grade RAG System

## Overview
PrivateGPT is a production-ready Retrieval-Augmented Generation (RAG) system built with microservices architecture, designed for enterprise deployment with comprehensive authentication, document management, and AI-powered chat capabilities.

**Current Phase**: UI and chat functionality fully operational. Model loading, chat endpoints, and API connectivity resolved. Authentication temporarily disabled for debugging. Core features working with Ollama integration and streaming chat interface.

## Architecture

### System Design
- **Pattern**: Domain-Driven Design (DDD) with Vertical Slice Architecture
- **Deployment**: Docker Compose orchestration with service isolation
- **Communication**: HTTP/REST APIs with centralized gateway routing
- **Authentication**: Keycloak OIDC/OAuth2 with JWT token validation
- **Data Flow**: API Gateway → Microservices → Vector Store/Database

### Core Services

#### 1. API Gateway (`gateway-service`)
**Purpose**: Centralized routing, authentication, and conversation management
- **Location**: `src/privategpt/services/gateway/`
- **Port**: 8000
- **Responsibilities**:
  - JWT token validation via Keycloak integration
  - Conversation and message management
  - MCP (Model Context Protocol) client integration
  - System prompt management with XML parsing
  - User session and chat history persistence

**Key Components**:
- `main.py`: FastAPI application with middleware stack
- `api/chat_router.py`: Conversation and message endpoints
- `api/prompt_router.py`: System prompt management
- `core/chat_service.py`: Conversation logic and LLM integration
- `core/mcp_client.py`: MCP client for tool execution
- `core/xml_parser.py`: Thinking brackets and UI tag parsing
- `core/prompt_manager.py`: Dynamic system prompt loading

#### 2. RAG Service (`rag-service`)
**Purpose**: Document processing, embedding, and retrieval
- **Location**: `src/privategpt/services/rag/`
- **Port**: 8002 (exposed on host; internal service listens on 8000)
- **Responsibilities**:
  - Document ingestion and chunking
  - Vector embedding generation
  - Semantic search and retrieval
  - Context-aware response generation

#### 3. LLM Service (`llm-service`)
**Purpose**: Ollama-based language model inference and generation
- **Location**: `src/privategpt/services/llm/`
- **Port**: 8003
- **Responsibilities**:
  - Ollama model management and initialization
  - Real-time streaming text generation
  - Chat conversation with context
  - Model parameter configuration (temperature, max_tokens)
  - Multi-model support and switching

**Implementation Details**:
- `adapters/ollama_adapter.py`: Full Ollama API integration with streaming
- `api/main.py`: FastAPI endpoints for /generate, /chat, /models
- Model: tinydolphin:latest (optimized for memory constraints)
- Features: Server-Sent Events for streaming, async HTTP with HTTPX

#### 4. UI Service (`ui-service`)
**Purpose**: Streamlit-based web interface with streaming chat
- **Location**: `src/privategpt/services/ui/`
- **Port**: 8080
- **Responsibilities**:
  - User authentication interface
  - Document upload and management
  - Real-time streaming LLM chat interface
  - RAG chat with document context
  - Admin panel for system management

**Key Features**:
- `pages/llm_chat.py`: Streaming chat with model selection and settings
- `utils/llm_client.py`: LLM service API client with streaming support
- Real-time response generation with typing indicators
- Model switching, temperature controls, generation settings
- Chat history with timestamps and performance metrics

### Infrastructure Services

#### Authentication (Keycloak)
- **Service**: `keycloak`
- **Port**: 8180
- **Database**: PostgreSQL (`keycloak-db`)
- **Configuration**: Automated realm import via `config/keycloak/realm-export.json`
- **Default Admin**: `admin@admin.com` / `admin` (configurable via `config.json`)
- **Features**:
  - OIDC/OAuth2 provider
  - User management and roles
  - JWT token issuance
  - Pre-configured realm with admin user
  - Admin console at `http://localhost:8180`

#### Language Model (Ollama)
- **Service**: `ollama`
- **Port**: 11434
- **Storage**: Persistent volume (`ollama_data`) for model files
- **Model Management**: Manual installation via `make install-model MODEL=<name>`
- **Features**:
  - Local LLM hosting with API compatibility
  - Model persistence between container restarts
  - Health checks and dependency management
  - No default models (install as needed)

#### Databases
- **Main Database**: PostgreSQL (`db`) - Application data
- **Keycloak Database**: PostgreSQL (`keycloak-db`) - Identity management
- **Vector Store**: Weaviate - Document embeddings and search
- **Cache**: Redis - Session storage and caching

#### Observability
- **Message Queue**: Celery with Redis backend
- **Monitoring**: Health check endpoints across all services
- **Logging**: Structured JSON logging with correlation IDs

## Enhanced Features (v2)

### Model Context Protocol (MCP) Integration
- **Local MCP Server**: STDIO-based tool execution for Ollama models
- **Available Tools**:
  - `search_documents`: Semantic search through uploaded documents
  - `read_file`: Read file contents with permission checks
  - `list_directory`: Browse directory structures
  - `create_file`: Create new files with content
  - `edit_file`: Modify existing files
  - `get_system_info`: System information and health checks
  - `check_service_health`: Monitor service status

### Advanced Chat Features
- **Thinking Display**: AI reasoning visualization (similar to DeepSeek R1)
- **Tool Call Tracking**: Real-time execution monitoring and results
- **Conversation Threading**: Persistent chat history with metadata
- **Model Switching**: Change models within conversations
- **System Prompt Management**: Dynamic prompts with XML structure
- **Response Parsing**: XML tag extraction for UI rendering

### Developer Testing Interface
- **Enhanced Dashboard**: Single-page testing hub with service monitoring
- **Debug Toggles**: Show/hide thinking content, tool calls, raw responses
- **JSON Viewers**: Complete API response inspection
- **API Testing**: Direct endpoint testing with authentication
- **Performance Metrics**: Response times, token usage, model statistics

### Database Schema (v2)
- **Conversations**: User chat sessions with model and prompt tracking
- **Messages**: Individual messages with tool calls and thinking content
- **Tool Calls**: Execution tracking with parameters and results
- **System Prompts**: XML-structured prompts with model pattern matching
- **Model Usage**: Token consumption and cost tracking

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
- **Middleware**: `KeycloakAuthMiddleware` for request interception (gateway-level)
- **Token Validation**: JWKS-based signature verification (gateway handles validation)
- **Role Extraction**: Claims parsing for authorization
- **Session Management**: Simplified session-based approach in UI, no external token validation
- **Authentication Flow**: Gateway validates tokens, UI manages local session state

## Development Workflow

### Build System
```bash
# Clean build (removes containers and volumes)
make clean

# Full build with automated setup
make build

# Start/stop services
make start
make stop

# Container and status management
make status
make clean-all  # Remove everything including volumes
```

### Model Management

**No Auto-Installation**: Models are not automatically downloaded during build.

```bash
# Install specific Ollama models
make install-model MODEL=llama3.2:1b
make install-model MODEL=llama3.2:3b
make install-model MODEL=mistral:7b
make install-model MODEL=codellama:7b

# List installed models
make list-models

# Remove specific models
make remove-model MODEL=llama3.2:1b
```

**Model Persistence**: Models are stored in the `ollama_data` Docker volume and persist across container restarts and `make clean` operations. Only `make clean-all` removes the models completely.

**Recommended Models**:
- `tinydolphin:latest` - Smallest, fastest (636MB) - **Currently working**
- `llama3.2:1b` - Requires 2.1GB memory (may exceed available resources)
- `llama3.2:3b` - Good balance of speed/quality (2GB)
- `llama3.2:7b` - Higher quality (4.7GB)

**Memory Considerations**: Some models require more system memory than available in default Docker configuration. Use `tinydolphin:latest` for development with limited resources.

### Service Dependencies
1. **Base Image**: `docker/base/Dockerfile` - Common Python dependencies
2. **Service Images**: Inherit from base for fast builds
3. **Health Checks**: All services implement `/health` endpoints
4. **Startup Order**: Database → Keycloak → Application Services

### Configuration Management

#### Pydantic Settings Model
- **Location**: `src/privategpt/shared/settings.py`
- **Type**: Pydantic BaseSettings with environment variable support
- **Features**: Type validation, automatic env var parsing, config file support

#### Configuration Files
- **Default Config**: `config.json` - Default settings for all services
- **Keycloak Realm**: `config/keycloak/realm-export.json` - Pre-configured authentication realm
- **Environment Variables**: Docker Compose `.env` support for overrides

#### Default Admin User
- **Email**: `admin@admin.com` (configurable via `DEFAULT_ADMIN_EMAIL`)
- **Password**: `admin` (configurable via `DEFAULT_ADMIN_PASSWORD`)
- **Automatic Creation**: Created during `make build` via realm import
- **Customization**: Update `config.json` or set environment variables

#### Configuration Hierarchy
1. **Environment Variables** (highest priority)
2. **config.json** file settings  
3. **Pydantic field defaults** (fallback)

#### Service Discovery
- **Internal**: Docker Compose networking with service hostnames
- **External**: Configurable URLs via settings
- **Secrets**: Keycloak client secrets, database credentials in environment

## API Documentation

### Gateway Endpoints
```
# Authentication (currently disabled for debugging)
POST /api/auth/login          # User authentication
POST /api/auth/verify         # Token validation
GET  /api/auth/me            # Current user profile
GET  /api/auth/keycloak/config # Frontend Keycloak config

# Chat Endpoints (working)
POST /api/chat/direct         # Direct LLM chat without persistence
POST /api/chat/mcp           # Chat with MCP tool integration
GET  /api/chat/conversations  # List user conversations
POST /api/chat/conversations  # Create new conversation

# Model Management (working)
GET  /api/llm/models         # List available models
POST /api/llm/generate       # Single text generation
POST /api/llm/chat          # Chat with conversation context

# Proxied service endpoints
/api/rag/*                   # RAG service operations
/api/admin/*                 # Administrative functions
```

### Service Communication
- **Internal**: HTTP with service hostnames (`http://rag-service:8000`)
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

#### Authentication Failures
1. **Cannot login with admin@admin.com**:
   - Check Keycloak setup logs: `make logs-keycloak-setup`
   - Verify realm import: `make logs-keycloak`
   - Restart Keycloak setup: `docker-compose up --no-deps keycloak-setup`

2. **Keycloak not accessible**:
   - Verify Keycloak is running: `make logs-keycloak`
   - Check port 8180 is accessible: `curl http://localhost:8180/health/ready`
   - Check Docker network connectivity

#### Service Connectivity
- Verify Docker network and health checks: `make status`
- Check service logs: `make logs-<service>`
- Restart specific services: `docker-compose restart <service>`

#### Database and Configuration
- **Database Migrations**: Ensure schema is up to date
- **Port Conflicts**: Check for conflicting services on host ports
- **Configuration Issues**: Verify `config.json` syntax and settings

### Debugging Commands
```bash
# Service logs
docker-compose logs -f gateway-service

# Database access
docker-compose exec db psql -U privategpt -d privategpt

# Keycloak admin
# URL: http://localhost:8180
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