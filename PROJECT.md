# PrivateGPT - Enterprise-Grade RAG System

## Overview
PrivateGPT is a production-ready Retrieval-Augmented Generation (RAG) system built with microservices architecture, designed for enterprise deployment with comprehensive authentication, document management, and AI-powered chat capabilities.

**Current Phase**: Production-ready microservices system with multi-provider LLM support, streaming chat, MCP tool integration, comprehensive token tracking system, and configuration management. Full authentication system implemented with Keycloak JWT integration. Complete conversation management APIs with SQLAlchemy async session support. Multi-provider (Ollama, OpenAI, Anthropic) architecture with dynamic model discovery and routing. Enhanced CORS support for error responses and configurable model lists for external providers.

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
  - Conversation and message management with token tracking
  - MCP (Model Context Protocol) client integration
  - System prompt management with XML parsing
  - User session and chat history persistence
  - Real-time token usage monitoring and context limit management
- **Core Endpoints**:
  - Authentication: Login, logout, token refresh/verify
  - User Management: Profile, preferences, admin operations
  - Conversation Management: CRUD operations with streaming support
  - System Prompts: Dynamic prompt management
  - Health Monitoring: Service status and health checks

**Key Components**:
- `main.py`: FastAPI application with middleware stack
- `api/chat_router.py`: Conversation and message endpoints with streaming support and token tracking
- `api/prompt_router.py`: System prompt management
- `core/chat_service.py`: Conversation logic, LLM integration, and token management
- `core/exceptions.py`: Comprehensive error handling with BaseServiceError hierarchy
- `core/error_handler.py`: Centralized error response formatting and security
- `core/mcp_client.py`: MCP client for tool execution
- `core/xml_parser.py`: Thinking brackets and UI tag parsing
- `core/prompt_manager.py`: Dynamic system prompt loading
- `core/stream_session.py`: Redis-based streaming session management

**Streaming Architecture (Two-Phase Approach)**:
- **Phase 1**: `/api/chat/conversations/{id}/prepare-stream` - Create user message, return stream token
- **Phase 2**: `/stream/{token}` - Pure streaming without database operations (mounted sub-app, no auth)
- **Persistence**: Celery task saves assistant message after streaming completes
- **Session Storage**: Redis caching with 5-minute TTL for stream sessions
- **Security**: Stream tokens are self-contained authentication (no JWT needed for phase 2)
- **Model Selection**: Model must be specified in prepare-stream request (required parameter)

#### 2. RAG Service (`rag-service`)
**Purpose**: Document processing, embedding, and retrieval with hierarchical collections
- **Location**: `src/privategpt/services/rag/`
- **Port**: 8002 (exposed on host; internal service listens on 8000)
- **Responsibilities**:
  - Hierarchical collection management (folders/subfolders)
  - Asynchronous document processing via Celery
  - Real-time progress tracking for document ingestion
  - Vector embedding generation (BAAI/bge-small-en-v1.5)
  - Semantic search with Weaviate vector store
  - Document chunking and metadata management
- **Key Features**:
  - Collections support nested folder structure with breadcrumb navigation
  - Celery-based background processing with progress states
  - Document status tracking (pending → processing → complete/failed)
  - Chunk storage with PostgreSQL and vector indexing
  - RESTful API for all operations

#### 3. LLM Service (`llm-service`)
**Purpose**: Ollama-based language model inference and generation
- **Location**: `src/privategpt/services/llm/`
- **Port**: 8003
- **Responsibilities**:
  - Ollama model management and initialization
  - Real-time streaming text generation with SSE support
  - Chat conversation with context and 180s timeout support
  - Model parameter configuration (temperature, max_tokens)
  - Multi-model support and switching

**Implementation Details**:
- **Multi-Provider Architecture**: `core/model_registry.py` - Central registry managing Ollama, OpenAI, and Anthropic providers
- **Provider Factory**: `core/provider_factory.py` - Dynamic provider creation from configuration
- **Adapters**: Provider-specific implementations (`ollama_adapter.py`, `openai_adapter.py`, `anthropic_adapter.py`)
- **Token Tracking**: `ChatResponse` dataclass with real-time token usage from all providers
- **Context Management**: Provider-specific context limits and validation (`get_context_limit()`, `count_tokens()`)
- **Model Discovery**: Automatic model discovery from all enabled providers with conflict resolution
- **Request Routing**: Intelligent routing based on model names to appropriate providers
- **Streaming Support**: Server-Sent Events across all providers with 600s timeout
- **Health Monitoring**: Comprehensive provider health checking and status reporting

#### 4. User Interfaces

**Next.js UI (Primary)**
- **Service**: `nextjs-ui`
- **Location**: `src/privategpt_ui/sandbox-ui/`
- **URL**: `http://localhost` (via Traefik)
- **Framework**: Next.js 15 + TypeScript + Tailwind CSS
- **Documentation**: See `src/privategpt_ui/sandbox-ui/PROJECT.md` for comprehensive UI documentation
- **Features**:
  - Full authentication integration with Keycloak
  - Zustand state management with persistence
  - Protected routes with AuthWrapper component
  - Custom API client with automatic token management
  - Real-time streaming chat with SSE support
  - Development hot reload via Docker volumes
  - Admin panel and document management

**Streamlit UI (Legacy)**  
- **Service**: `ui-service`
- **Location**: `src/privategpt/services/ui/`
- **URL**: `http://localhost/streamlit` (via Traefik)
- **Framework**: Streamlit

**Shared Responsibilities**:
  - User authentication interface
  - Document upload and management
  - Real-time streaming LLM chat interface
  - RAG chat with document context
  - Admin panel for system management

**Key Features**:
- `pages/llm_chat.py`: Streaming chat with model selection and real-time display
- `utils/llm_client.py`: LLM service API client with streaming support
- Real-time response generation with typing indicators (`▋`)
- Model switching, temperature controls, generation settings
- Chat history with timestamps and performance metrics
- SSE-based streaming with 180s timeout for slow models
- Tool integration with MCP chat modes

### Infrastructure Services

#### Redis Cache
- **Service**: `redis`
- **Port**: 6379 (internal)
- **Image**: `redis:7-alpine`
- **Purpose**: 
  - Celery task broker and backend
  - Stream session storage for two-phase streaming
  - General caching and session management
- **Features**:
  - Automatic key expiration with TTL
  - High-performance in-memory storage
  - Pub/sub support for real-time features

#### Celery Worker
- **Service**: `celery-worker`
- **Purpose**: Background task processing
- **Responsibilities**:
  - Save assistant messages after streaming completes
  - Document ingestion and processing
  - Cleanup expired stream sessions
- **Configuration**:
  - Uses Redis as broker and backend
  - Runs from gateway Dockerfile with Celery command
  - Uses synchronous database operations to avoid event loop conflicts
  - Separate sync repositories for reliable background processing

#### Reverse Proxy (Traefik)
- **Service**: `traefik`
- **Port**: 80 (web), 8090 (dashboard)
- **Purpose**: HTTP reverse proxy and load balancer
- **Features**:
  - Automatic service discovery via Docker labels
  - Path-based routing (`/streamlit` → Streamlit UI)
  - Host-based routing (`localhost` → Next.js UI)
  - Dashboard at `http://localhost:8090/dashboard/`

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

## Streaming Architecture (v2.2)

### Two-Phase Streaming with Conversation Persistence

The system implements a two-phase streaming approach to solve SQLAlchemy async context limitations while maintaining conversation persistence:

#### Phase 1: Preparation (`/api/chat/conversations/{id}/prepare-stream`)
- Creates user message in database
- Retrieves conversation history
- Generates unique stream token
- Stores session data in Redis (5-minute TTL)
- Returns stream token and URLs
- **Required**: Model must be specified in request (no defaults)

#### Phase 2: Streaming (`/stream/{token}`)
- Mounted as sub-application (bypasses auth middleware)
- No database operations during streaming
- Validates token from Redis (token IS the authentication)
- Streams LLM response via Server-Sent Events
- Parses XML tags (thinking brackets, UI tags)
- Queues Celery task to save assistant message
- Cleans up Redis session after completion

#### Key Implementation Details
- **Streaming Router**: `src/privategpt/services/gateway/api/streaming_router.py`
- **No Auth on Stream**: Stream endpoint mounted as sub-app at `/stream` to bypass JWT middleware
- **Self-Contained Tokens**: Stream tokens contain all necessary auth/session data
- **Model Requirement**: Model parameter is mandatory in prepare-stream request
- **XML Parsing**: Supports `<thinking>` tags and UI formatting tags

#### Benefits
- **Solves SQLAlchemy Issues**: Complete separation of DB operations from streaming
- **Conversation Persistence**: All messages saved properly
- **Token Tracking**: Accurate token counting for usage analytics
- **Security**: Stream tokens provide authentication without JWT complexity
- **Frontend Friendly**: Works with EventSource API without auth headers
- **Scalability**: Redis-based sessions with automatic expiration
- **Reliability**: Celery ensures messages are saved even if client disconnects

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

## RAG System Architecture

### Collections System
- **Hierarchical Structure**: Nested folder organization for documents
- **Path Management**: Automatic path calculation and breadcrumb generation
- **Metadata Support**: Icons, colors, descriptions, and custom settings
- **Recursive Operations**: Document counting across collection trees
- **Soft Delete**: Collections marked as deleted, hard delete removes all data

### Document Processing Pipeline
1. **Upload**: Document uploaded to collection with metadata
2. **Task Creation**: Celery task queued with document ID and content
3. **Text Splitting**: Content divided into chunks (1000 chars, 200 overlap)
4. **Embedding Generation**: BAAI/bge-small-en-v1.5 model creates 384-dim vectors
5. **Vector Storage**: Embeddings stored in Weaviate with metadata
6. **Chunk Storage**: Text chunks saved to PostgreSQL with positions
7. **Progress Updates**: Real-time status via Celery state updates

### Progress Tracking States
- **PENDING**: Task queued, waiting for worker
- **PROGRESS**: Active processing with stage details:
  - `splitting`: Text chunking in progress
  - `embedding`: Generating vector embeddings
  - `storing`: Saving to vector database
  - `finalizing`: Updating document status
- **SUCCESS**: Processing complete, chunks ready
- **FAILURE**: Error occurred, details in document record

### API Endpoints
- **Collections**:
  - `GET /collections` - List user collections with counts
  - `POST /collections` - Create new collection
  - `GET /collections/{id}` - Get collection details
  - `PATCH /collections/{id}` - Update collection metadata
  - `DELETE /collections/{id}` - Delete collection (soft/hard)
  - `GET /collections/{id}/breadcrumb` - Get path hierarchy
  - `PATCH /collections/{id}/move` - Move to different parent
- **Documents**:
  - `POST /collections/{id}/documents` - Upload document
  - `GET /documents/{id}/status` - Get processing status
  - `GET /progress/{task_id}` - Real-time progress updates
- **Search**:
  - `POST /chat` - Query documents with semantic search

## Data Models

### Core Domain Entities

#### Collection (`src/privategpt/core/domain/collection.py`)
```python
class Collection:
    id: str  # UUID
    user_id: int
    parent_id: Optional[str]
    name: str
    description: Optional[str]
    collection_type: str  # 'collection' or 'folder'
    icon: Optional[str]
    color: Optional[str]
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

#### Document (`src/privategpt/core/domain/document.py`)
```python
class Document:
    id: int
    collection_id: Optional[str]
    user_id: int
    title: str
    file_path: str
    file_name: str
    file_size: int
    mime_type: str
    status: DocumentStatus  # pending, processing, complete, failed
    error: Optional[str]
    task_id: Optional[str]
    processing_progress: Dict[str, Any]
    doc_metadata: Dict[str, Any]
    uploaded_at: datetime
```

#### Chunk (`src/privategpt/core/domain/chunk.py`)
```python
class Chunk:
    id: int
    document_id: int
    position: int
    text: str
    embedding: Optional[List[float]]
    chunk_metadata: Dict[str, Any]
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
- **Architecture**: Backend exclusively handles real Keycloak authentication, frontend provides demo mode for offline development
- **Request Tracking**: `RequestIDMiddleware` adds unique IDs to all requests for tracing
- **Error Security**: Production mode hides internal error details, development shows full context
- **CORS Handling**: Enhanced CORS middleware ordering and explicit headers in error handlers ensure CORS support for all responses including errors

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

#### Unified Settings System
- **Location**: `src/privategpt/shared/settings.py`
- **Type**: Enhanced Pydantic BaseSettings with multi-provider support
- **Features**: 
  - Type validation and environment variable overrides
  - Multi-provider LLM configuration (Ollama, OpenAI, Anthropic)
  - Dynamic model registry initialization
  - MCP tool configuration with enable/disable flags
  - System prompt management and thinking mode controls

#### Configuration Files
- **Default Config**: `config.json` - Comprehensive multi-provider settings
- **Keycloak Realm**: `config/keycloak/realm-export.json` - Pre-configured authentication realm
- **Environment Variables**: Docker Compose `.env` support for overrides
- **MCP Tools**: Dynamic tool discovery with configurable availability
- **Model Lists**: Configurable arrays for OpenAI and Anthropic models via `openai_models` and `anthropic_models` in config.json

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

#### Error Handling
All API endpoints now return standardized error responses:
```json
{
  "error": {
    "type": "error_category",
    "code": "ERROR_CODE",
    "message": "User-friendly message",
    "details": { /* optional structured details */ },
    "suggestions": [ /* helpful suggestions */ ],
    "request_id": "uuid",
    "timestamp": "ISO-8601"
  }
}
```

Error Categories:
- `context_limit_error` (413) - Token limit exceeded
- `resource_error` (503) - Memory/compute exhausted  
- `model_error` (404) - Model not available
- `validation_error` (400) - Invalid input
- `rate_limit_error` (429) - Rate limit exceeded
- `service_unavailable` (503) - Downstream service issues
- `configuration_error` (500) - Missing configuration
- `auth_error` (401/403) - Authentication/authorization failures

```
# Health & Status
GET  /                        # API root/welcome message
GET  /health                  # Gateway health check
GET  /health/{service}        # Check health of specific service
GET  /status                  # Detailed gateway status with services

# Authentication
POST /api/auth/login          # User authentication
POST /api/auth/verify         # Token validation
POST /api/auth/refresh        # Token refresh
POST /api/auth/logout         # User logout
GET  /api/auth/me            # Current user profile (deprecated, use /api/users/me)
GET  /api/auth/keycloak/config # Frontend Keycloak config

# User Management
GET  /api/users/me            # Get current user profile
PUT  /api/users/me            # Update current user profile
GET  /api/users/me/preferences # Get user preferences
PUT  /api/users/me/preferences # Update user preferences
GET  /api/users               # List all users (admin only)
GET  /api/users/{user_id}     # Get specific user (admin only)
DELETE /api/users/{user_id}   # Delete user (admin only)

# System Prompts
GET  /api/prompts             # List all prompts
GET  /api/prompts/{prompt_id} # Get specific prompt
POST /api/prompts             # Create new prompt
PATCH /api/prompts/{prompt_id} # Update prompt
DELETE /api/prompts/{prompt_id} # Delete prompt
GET  /api/prompts/for-model/{model_name} # Get prompt for specific model
POST /api/prompts/test        # Test prompt with model
POST /api/prompts/initialize-defaults # Initialize default prompts

# Chat Endpoints (working with streaming)
POST /api/chat/direct         # Direct LLM chat without persistence
POST /api/chat/direct/stream  # Direct LLM chat with Server-Sent Events
POST /api/chat/mcp           # Chat with MCP tool integration
POST /api/chat/mcp/stream    # MCP chat with streaming support

# Conversation Management (with persistence)
GET  /api/chat/conversations  # List user conversations
POST /api/chat/conversations  # Create new conversation
GET  /api/chat/conversations/{id}  # Get specific conversation
PATCH /api/chat/conversations/{id}  # Update conversation metadata
DELETE /api/chat/conversations/{id}  # Delete conversation
GET  /api/chat/conversations/{id}/messages  # List messages in conversation
POST /api/chat/conversations/{id}/messages  # Create new message
POST /api/chat/conversations/{id}/chat  # Send message and get response
POST /api/chat/conversations/{id}/chat/stream  # Send message with streaming response
POST /api/chat/conversations/{id}/prepare-stream  # Phase 1: Prepare streaming session
GET  /stream/{token}  # Phase 2: Stream response (no DB operations)
POST /api/chat/webhooks/stream-completion  # Optional webhook for stream completion

# Model Management (multi-provider)
GET  /api/llm/models         # List models from all enabled providers
POST /api/llm/generate       # Single text generation with provider routing
POST /api/llm/chat          # Chat with conversation context and streaming

# Proxied service endpoints
/api/rag/*                   # RAG service operations
/api/admin/*                 # Administrative functions
```

### Service Communication
- **Internal**: HTTP with service hostnames (`http://rag-service:8000`, `http://llm-service:8000`)
- **External**: Gateway exposure on `localhost:8000`
- **Model Registry**: Dynamic provider registration and health monitoring
- **Authentication**: Bearer token propagation (currently disabled for debugging)
- **Error Handling**: Standardized HTTP status codes with provider-specific error mapping
- **Load Balancing**: Model-based request routing to appropriate providers

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
  celery-worker:       # Background task processing
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
- **Two-Phase Streaming**: Separation of database operations from streaming response

### Technology Stack
- **Backend**: FastAPI + SQLAlchemy 2.0 + Pydantic Settings
- **Frontend**: Streamlit with multi-provider model selection
- **Identity**: Keycloak for enterprise SSO integration (temporarily disabled)
- **Vector Search**: Weaviate for semantic similarity
- **Embeddings**: Sentence Transformers (BGE models)
- **LLM Integration**: Multi-provider registry (Ollama, OpenAI, Anthropic)
- **Model Context Protocol**: Local MCP server with STDIO transport
- **Configuration**: Unified config.json + environment variable system

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

3. **"Network error: Failed to fetch" in UI**:
   - Verify API URL configuration in `docker-compose.yml`
   - Ensure base URL doesn't include `/api` suffix: `NEXT_PUBLIC_API_URL=http://localhost:8000`
   - Check that API endpoints in frontend include `/api` prefix (e.g., `/api/auth/login`)
   - Test backend directly: `curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@admin.com","password":"admin"}'`
   - See `src/privategpt_ui/sandbox-ui/PROJECT.md` for detailed UI troubleshooting

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
  - Conversation repository with async session handling
  - Message CRUD operations with eager loading
  - Domain model conversions
- **Integration Tests**: Service interaction testing
  - JWT authentication flow with Keycloak
  - Conversation management API endpoints
  - User auto-creation from Keycloak claims
- **End-to-End Tests**: Full workflow validation
- **Authentication Tests**: Token validation flows
- **Test Commands**:
  ```bash
  make test              # Run all tests
  make test-conversation # Run conversation tests
  make test-auth        # Run authentication tests
  make test-integration # Run integration tests
  ```

### Security Considerations
- **Input Validation**: Pydantic models for data validation
- **SQL Injection**: Parameterized queries via SQLAlchemy
- **XSS Protection**: Content Security Policy headers
- **CSRF Protection**: Token-based authentication
- **Data Encryption**: TLS for all external communication

This system provides a robust foundation for enterprise RAG applications with comprehensive authentication, scalable microservices architecture, and production-ready deployment capabilities.