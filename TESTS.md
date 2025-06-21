# Comprehensive Test Coverage Plan for PrivateGPT

## Overview
Based on analysis of the codebase, here's a comprehensive testing strategy covering unit, integration, and end-to-end tests for all critical components.

## Current State
- ✅ Basic pytest setup with conftest.py
- ✅ SQLite in-memory database fixture
- ✅ Minimal auth service tests
- ⚠️ Coverage gaps across 90% of codebase

## Testing Strategy

### Phase 1: Domain Layer Unit Tests (High Priority)
**Core business entities with pure business logic**
- `core/domain/conversation.py` - conversation management methods
- `core/domain/message.py` - message validation and processing  
- `core/domain/document.py` - document metadata handling
- `core/domain/chunk.py` - text chunking logic
- `core/domain/tool_call.py` - tool execution tracking

### Phase 2: Infrastructure Layer Tests (Critical)
**External dependencies and adapters requiring mocking**

**Database Repositories:**
- `infra/database/conversation_repository.py` - async CRUD operations
- `infra/database/message_repository.py` - message persistence
- `infra/database/document_repository.py` - document storage
- `infra/database/chunk_repository.py` - vector chunk management

**LLM Adapters:**
- `services/llm/adapters/ollama_adapter.py` - HTTP client mocking
- `services/llm/adapters/openai_adapter.py` - API response mocking
- `services/llm/adapters/anthropic_adapter.py` - streaming response tests

**Vector Store & Embedders:**
- `infra/vector_store/weaviate_adapter.py` - vector search operations
- `infra/embedder/bge_adapter.py` - embedding generation

### Phase 3: Service Layer Tests (High Priority)
**Complex business logic coordination**

**Gateway Services:**
- `services/gateway/core/chat_service.py` - conversation orchestration
- `services/gateway/core/mcp_client.py` - tool execution logic
- `services/gateway/core/xml_parser.py` - content parsing
- `services/gateway/core/prompt_manager.py` - prompt templates

**RAG Services:**
- `services/rag/core/service.py` - document processing pipeline
- Text splitters and chunking strategies

### Phase 4: API Integration Tests (Medium Priority)  
**FastAPI endpoint testing with test client**

**Gateway Endpoints:**
- `/api/chat/*` - chat and streaming endpoints
- `/api/auth/*` - authentication flows  
- `/api/prompts/*` - system prompt management

**Service Endpoints:**
- LLM service API endpoints
- RAG service document upload/search
- Health check endpoints

### Phase 5: End-to-End Tests (Medium Priority)
**Full workflow validation with Docker Compose**
- Complete chat conversations with streaming
- Document upload → RAG retrieval → chat
- MCP tool execution workflows
- Authentication integration flows

## Testing Infrastructure Enhancements

### Test Organization
```
tests/
├── unit/
│   ├── domain/          # Pure business logic
│   ├── infra/           # Infrastructure adapters  
│   ├── services/        # Service layer logic
│   └── shared/          # Shared utilities
├── integration/
│   ├── api/             # FastAPI endpoint tests
│   ├── database/        # Database integration
│   └── external/        # External service mocks
└── e2e/
    ├── chat_flows/      # Complete chat scenarios
    ├── rag_workflows/   # Document processing flows
    └── auth_integration/ # Authentication scenarios
```

### Test Utilities & Fixtures
- **Enhanced conftest.py**: Async database, HTTP clients, external service mocks
- **Factory classes**: Test data generation for entities
- **Mock clients**: Ollama, Keycloak, Weaviate service mocks
- **Streaming test helpers**: SSE response validation
- **Authentication fixtures**: JWT token generation for tests

### Coverage Targets
- **Domain Layer**: 95% coverage (pure functions)
- **Infrastructure**: 85% coverage (external dependencies)
- **Services**: 90% coverage (business logic)
- **APIs**: 80% coverage (integration points)
- **Overall Target**: 85% code coverage

### Tools & Configuration
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking framework
- **httpx**: Async HTTP client testing
- **pytest-docker**: Container integration tests
- **Coverage reporting**: HTML reports with missed lines

### Implementation Approach
1. **Start with domain tests** - fastest wins, pure logic
2. **Mock external dependencies** - Ollama, Keycloak, Weaviate
3. **Build test data factories** - consistent test data
4. **Add integration tests gradually** - one service at a time
5. **End-to-end tests last** - full system validation

This plan provides comprehensive coverage while being practical to implement incrementally, starting with high-value, low-complexity domain tests and building up to full system integration testing.

## Test Implementation Priority

### Immediate (Week 1)
- [ ] Domain entity unit tests (conversation, message, document)
- [ ] Enhanced conftest.py with async fixtures
- [ ] Test data factories for core entities

### Short-term (Week 2-3)
- [ ] Database repository tests with mocked dependencies
- [ ] LLM adapter tests with HTTP mocking
- [ ] Chat service orchestration tests

### Medium-term (Month 1)
- [ ] API endpoint integration tests
- [ ] Streaming response validation tests
- [ ] MCP tool execution tests

### Long-term (Month 2+)
- [ ] End-to-end workflow tests
- [ ] Performance and load testing
- [ ] Security testing for authentication flows

## Success Metrics
- Achieve 85% overall code coverage
- All CI/CD builds include automated test execution
- Zero critical bugs in production due to comprehensive test coverage
- Fast developer feedback loop with sub-30-second test execution