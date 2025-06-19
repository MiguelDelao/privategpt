# Claude AI Collaboration Guide

This file provides context and guidelines for AI assistants working on the PrivateGPT project.

## Project Overview
PrivateGPT v2 is a self-hosted RAG (Retrieval-Augmented Generation) system with vertical-slice microservices architecture. The system processes documents into searchable chunks and provides AI-powered question answering while maintaining privacy.

## Architecture Principles
- **Domain-Driven Design**: Clear separation between core domain and infrastructure
- **Ports & Adapters**: Infrastructure abstraction for testability and flexibility
- **Vertical Slices**: Independent services (auth, rag, llm, ui) with their own APIs
- **Async-First**: Non-blocking operations throughout the stack

## Key Directories
- `src/privategpt/core/`: Domain models and business logic
- `src/privategpt/infra/`: Infrastructure adapters (database, vector store, etc.)
- `src/privategpt/services/`: Independent service implementations
- `docs/contexts/`: Rich domain context for AI assistants
- `docs/decisions/`: Architectural decision records
- `docs/constraints/`: Hard rules and boundaries

## When Working on This Codebase
1. **Always read relevant context files** in `docs/contexts/` before making changes
2. **Check constraints** in `docs/constraints/` to avoid violations
3. **Follow existing patterns** - this is a well-architected system
4. **Use async/await** consistently
5. **Maintain type hints** and modern Python practices

## Services Overview
- **Auth Service** (port 8001): JWT-based authentication
- **RAG Service** (port 8002): Document processing and question answering
- **UI Service** (port 8501): Streamlit web interface
- **LLM Service**: Language model integration (placeholder)

## Testing Strategy
- Unit tests in `tests/unit/`
- Integration tests run via Docker
- Use fake adapters for testing infrastructure components

## Deployment
- Docker Compose with comprehensive observability
- ELK stack for logging and monitoring
- Traefik for reverse proxy and routing

Refer to specific context files for detailed domain knowledge and decision rationale.