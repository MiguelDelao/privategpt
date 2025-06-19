# PrivateGPT v2 System Overview

*Living document - Single source of truth for system state and architecture*

## Current System State

### Core Services (Production Ready)
- ✅ **Auth Service**: JWT authentication with PostgreSQL user store
- ✅ **RAG Service**: Document processing pipeline with BGE embeddings + Weaviate
- ✅ **UI Service**: Streamlit multi-page application with authentication
- 🔄 **LLM Service**: Placeholder implementation (echo adapter)

### Infrastructure Status
- ✅ **Database**: PostgreSQL with SQLAlchemy 2.0 (async)
- ✅ **Vector Store**: Weaviate for semantic search
- ✅ **Task Queue**: Redis + Celery for background processing
- ✅ **Observability**: ELK stack with structured logging
- ✅ **Deployment**: Docker Compose with Traefik routing

### Current Capabilities
1. **Document Upload**: PDF/text file ingestion via REST API
2. **Document Processing**: Chunking → BGE embeddings → Weaviate storage
3. **Semantic Search**: Vector similarity search with metadata filtering
4. **RAG Chat**: Question answering with document context (using echo LLM)
5. **User Management**: Registration, login, role-based access
6. **Admin Interface**: Document management and system monitoring

## Architecture Highlights

### Domain Model
```
Document → Chunks → Embeddings → Vector Store
                ↓
User Query → Vector Search → Context + LLM → Answer
```

### Service Communication
- REST APIs between services
- Async task processing for heavy operations
- Shared PostgreSQL for transactional data
- Independent scaling per service

## Known Issues & Technical Debt

### Security (Critical)
- Hardcoded credentials in docker-compose.yml
- Overly permissive CORS settings
- Missing secrets management

### Architecture
- Embedding storage as JSON strings (should use vector types)
- No database migrations (only create_all)
- Inconsistent service URLs in configuration

### Observability
- Basic health checks need enhancement
- Missing application metrics beyond logging
- No alerting system configured

## Immediate Priorities
1. **Security hardening**: Environment-based secrets, CORS restrictions
2. **LLM integration**: Replace echo adapter with real LLM provider
3. **Database migrations**: Proper schema versioning with Alembic
4. **Vector storage optimization**: Native vector types vs JSON

## Technology Stack
- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic
- **Database**: PostgreSQL, Redis, Weaviate
- **AI/ML**: sentence-transformers (BGE), torch
- **Frontend**: Streamlit
- **Infrastructure**: Docker, Traefik, ELK stack
- **Task Processing**: Celery

*Last updated: 2025-01-19*