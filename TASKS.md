# PrivateGPT v2 Development Tasks

## Status Overview

| Phase | Status | Progress |
|-------|--------|----------|
| Core Infrastructure | ✅ Complete | 100% |
| Authentication & Gateway | ✅ Complete | 90% |
| Multi-Provider LLM Integration | ✅ Complete | 100% |
| Model Registry & Discovery | ✅ Complete | 100% |
| Configuration Management | ✅ Complete | 100% |
| UI Chat Functionality | ✅ Complete | 100% |
| Chat Endpoints | ✅ Complete | 100% |
| Streaming Chat Support | ✅ Complete | 100% |
| Two-Phase Streaming Architecture | ✅ Complete | 100% |
| MCP Integration | ✅ Complete | 100% |
| Advanced Chat Features | ✅ Complete | 95% |
| Token Tracking & Context Management | ✅ Complete | 100% |
| Developer Testing Interface | ✅ Complete | 100% |
| RAG Functionality | 🔄 In Progress | 80% |
| Production Gateway APIs | ✅ Complete | 95% |
| Test Coverage Implementation | ⏳ Planned | 5% |
| React/Next.js UI | ✅ Complete | 95% |

---

## ✅ Recently Completed

### Two-Phase Streaming Architecture & API Enhancements (Jun 24, 2025)
- [x] **Redis integration for stream session storage**
- [x] **Stream session manager with TTL-based expiration**
- [x] **Phase 1 endpoint**: `/api/chat/conversations/{id}/prepare-stream`
- [x] **Phase 2 endpoint**: `/stream/{token}` - Mounted sub-app with no auth
- [x] **Celery task for saving assistant messages after streaming**
- [x] **Complete separation of database operations from streaming**
- [x] **Self-contained stream tokens** - Token IS the authentication
- [x] **Automatic cleanup of expired sessions**
- [x] **Full conversation persistence with accurate token tracking**
- [x] **Model parameter required** - No hardcoded defaults
- [x] **XML parsing support** - Thinking brackets and UI tags
- [x] **Frontend-friendly design** - Works with EventSource API
- [x] **Delete conversation endpoint** - Support for soft and hard delete with `?hard_delete=true`

### Authentication & Database Implementation (Jun 21-23, 2025)
- [x] **Full authentication flow with Keycloak integration**
- [x] **Auth router with login, verify, refresh, logout endpoints**
- [x] **JWT token validation and management with proper Keycloak configuration**
- [x] **Protected routes with AuthWrapper component**
- [x] **User auto-creation with keycloak_id mapping**
- [x] **SQLAlchemy async session MissingGreenlet error resolution**
- [x] **Context manager pattern implementation for database operations**
- [x] **Eager loading with selectinload to prevent lazy loading issues**
- [x] **Complete conversation management API with JWT authentication**
- [x] **Token tracking and conversation persistence working end-to-end**

### Next.js UI Integration (Jun 21, 2025)
- [x] **Next.js 15 + TypeScript + Tailwind CSS frontend**
- [x] **Docker containerization with development mode**
- [x] **Traefik reverse proxy routing configuration**
- [x] **API client for PrivateGPT backend integration**
- [x] **Authentication state management with Zustand**
- [x] **Server-Sent Events support for streaming**
- [x] **Volume mounting for hot reload development**
- [x] **Dual UI setup: Next.js (primary) + Streamlit (legacy)**

### Multi-Provider LLM System (Dec 20-21, 2024)
- [x] **Complete multi-provider architecture implemented**
- [x] **Model registry with Ollama, OpenAI, and Anthropic support**
- [x] **Dynamic model discovery and conflict resolution**
- [x] **Provider factory with configuration-driven initialization**
- [x] **Intelligent request routing based on model names**
- [x] **Health monitoring across all providers**
- [x] **Unified configuration system (config.json + env vars)**
- [x] Fixed Streamlit UI with multi-provider model selection
- [x] Resolved chat endpoint connectivity issues
- [x] Cleaned up API endpoint paths (/api/chat/direct, /api/chat/mcp)
- [x] Authentication temporarily disabled for debugging
- [x] **Server-Sent Events streaming across all providers**
- [x] **Real-time response display with typing indicators**
- [x] **600-second timeout support for slow models**
- [x] **Streaming endpoints: /api/chat/direct/stream and /api/chat/mcp/stream**

### MCP (Model Context Protocol) Integration
- [x] Local MCP server implementation with STDIO transport
- [x] Tool suite: document search, file operations, system info
- [x] MCP client integration with Ollama models
- [x] Tool call execution tracking and result display

### Advanced Chat Features
- [x] Thinking display with XML parsing (DeepSeek R1 style)
- [x] Tool call visualization and execution monitoring
- [x] Conversation persistence with metadata
- [x] System prompt management with XML structure
- [x] Model switching within conversations
- [x] Response parsing for UI rendering tags

### Enhanced Database Schema
- [x] Conversation and message models with tool call support
- [x] System prompt storage with pattern matching
- [x] Model usage tracking and analytics
- [x] Tool call execution history
- [x] User session and authentication state
- [x] **Token tracking with conversation-level aggregation (total_tokens)**
- [x] **Message-level token counting for usage analytics**

### Token Tracking & Context Management System (Jun 22, 2025)
- [x] **ChatResponse dataclass with input/output/total token tracking**
- [x] **Provider-specific token counting (tiktoken for OpenAI, estimation for Ollama)**
- [x] **Real-time context limit validation before LLM requests**
- [x] **ChatContextLimitError with detailed error messages and suggestions**
- [x] **Conversation total_tokens field with running totals**
- [x] **Database schema migration for token tracking support**
- [x] **End-to-end token tracking from API to database**
- [x] **HTTP 413 error responses with context limit information**
- [x] **GATEWAY.md documentation updated with token tracking API contract**

### Developer Testing Interface
- [x] Simplified single-page dashboard
- [x] Service health monitoring and status checks
- [x] Debug toggles for thinking, tool calls, raw responses
- [x] JSON viewers for complete API inspection
- [x] Direct API endpoint testing interface
- [x] Performance metrics and response time tracking

### Production Gateway APIs
- [x] Chat conversation management endpoints
- [x] System prompt CRUD operations
- [x] Authentication middleware with Keycloak
- [x] MCP integration with local tool execution
- [x] Error handling and logging infrastructure

---

## 🔄 In Progress

### Production Hardening (High Priority)  
- [x] Re-enable authentication with full Keycloak integration
- [x] Remove debug code from authentication middleware (prints and excessive logging)
- [x] **Implement standardized error handling** - BaseServiceError hierarchy with consistent format
- [x] **Add request ID tracking** - RequestIDMiddleware for tracing across services
- [x] **Enhance error security** - Hide internal details in production mode
- [ ] **CRITICAL: Secure debug endpoints** - Remove authentication bypass for `/api/chat/debug/` and `/api/test/`
- [ ] **CRITICAL: Remove hardcoded values** - User ID 1 in testing scenarios, magic numbers
- [ ] **CRITICAL: Implement secret management** - Move API keys to environment variables
- [ ] **CRITICAL: Remove default admin credentials** from hardcoded config
- [ ] Add comprehensive input validation and API key validation
- [ ] Security audit and vulnerability testing
- [ ] Provider-specific error handling and retry logic
- [ ] Rate limiting for external API providers
- [ ] Cost tracking and usage monitoring for cloud providers
- [ ] Increase Docker memory allocation for larger models

### Technical Debt Cleanup (Medium Priority)
- [ ] **CRITICAL: Fix Traefik Routing** - Gateway service not discoverable through Traefik proxy
  - Frontend currently requires direct gateway access (localhost:8000/api) 
  - Production should use clean URLs through proxy (localhost/api)
  - Traefik labels configured but service discovery failing
  - **Impact**: Different routing in dev vs production, hardcoded ports in frontend
- [ ] **Session Management**: Standardize on context manager pattern vs dependency injection
- [ ] **Error Handling**: Implement consistent error response format across all endpoints
- [ ] **Code Quality**: Remove hardcoded magic numbers (timeouts: 180s, 600s; limits: 1000, 4096)
- [ ] **TODO Completion**: Complete MCP integration implementation (remove TODO comments)
- [ ] **API Consistency**: Implement quick-chat endpoint (currently returns 501)
- [ ] **Database Patterns**: Remove raw SQL from business logic, use ORM consistently

### RAG Functionality (Medium Priority)
- [x] Connect RAG service to API gateway
- [x] Implement document upload and processing
- [x] Vector search integration with chat
- [ ] Document management UI improvements

---

## ⏳ Planned

### Test Coverage Implementation (Medium Priority)
**Focus Areas Based on Architecture Review:**
- [ ] **Core Conversation Management Tests** - Create, read, update, delete operations with database
- [ ] **JWT Authentication Flow Tests** - Token validation, user creation, role checking
- [ ] **Database Repository Integration Tests** - SQLAlchemy async session patterns
- [ ] **Multi-provider LLM Integration Tests** - Ollama, OpenAI, Anthropic provider switching
- [ ] **API Error Handling Tests** - Consistent error response format validation
- [ ] **Security Tests** - Authentication bypass prevention, input validation
- [ ] Performance and load testing for streaming endpoints (lower priority)
- [ ] End-to-end workflow testing with Docker Compose (lower priority)

### Next.js UI Chat Features (High Priority)
- [ ] Real-time chat interface integration with backend
- [ ] Message streaming with SSE support
- [ ] Model selection and switching UI
- [ ] Chat history and conversation management
- [ ] Document management with drag & drop
- [ ] Advanced chat history with tool calls visualization
- [ ] Responsive design and mobile support

### Tool Configuration & Management (Medium Priority)
- [x] **MCP local server with STDIO transport implemented**
- [x] **Tool suite available: document search, file operations, system info**
- [x] **Dynamic tool execution with result tracking**
- [ ] Remove hardcoded tool lists from UI components
- [ ] Implement dynamic tool discovery from MCP server
- [ ] Design tool selection UX (per-chat vs user preferences - TBD)
- [ ] Create tool factory system for runtime tool enablement
- [ ] Centralize tool-related configuration appropriately
- [ ] Consider tool categories and enhanced tool-specific settings

**Note**: Current implementation with hardcoded tools is working. UX for tool selection still being explored - may involve per-chat tool selection, user preferences, or other approaches.

### Advanced Features (Medium Priority)
- [x] ~~Real-time streaming with WebSocket/SSE~~ ✅ **Completed - SSE streaming working**
- [ ] Chat export and sharing capabilities
- [ ] Advanced system prompt templates
- [ ] Model performance analytics dashboard
- [ ] Multi-user conversation support

### Testing & Quality (Medium Priority)
- [ ] Integration test suite for MCP features
- [ ] Load testing for enhanced chat pipeline
- [ ] Security testing for tool execution
- [ ] Performance benchmarking with thinking/tools

---

## 🚧 Known Issues

### Model Memory Constraints
- **Ollama Memory Limits**: Some models (llama3.2:1b) require more memory than available
- **Docker Resource Allocation**: Default 2GB limit insufficient for larger models
- **Workaround**: Use tinydolphin:latest for development (636MB)

### Authentication ✅ Fixed  
- **JWT Authentication**: ✅ **Complete** - Full Keycloak integration with proper token validation
- **Keycloak Configuration**: ✅ **Fixed** - Issuer URL and audience validation corrected
- **User Management**: ✅ **Implemented** - Auto-user creation with keycloak_id mapping
- **Protected Routes**: ✅ **Working** - All conversation endpoints require valid JWT
- **Token Generation**: ✅ **Script Created** - get-jwt-token.sh for easy testing

### Database Layer ✅ Fixed
- **SQLAlchemy Async Issues**: ✅ **Fixed** - SQLAlchemy MissingGreenlet error resolved using context manager pattern
- **Context Manager Pattern**: ✅ **Implemented** - Replaced dependency injection with get_async_session_context()
- **Eager Loading**: ✅ **Added** - selectinload(Conversation.messages) prevents lazy loading issues
- **Schema Updates**: ✅ **Completed** - Manual migration for total_tokens field
- **User Authentication Integration**: ✅ **Fixed** - Proper keycloak_id lookup and auto-user creation
- **Enum vs String Status**: ✅ **Fixed** - Corrected status field handling to use string values
- **Streaming Context Issues**: ✅ **Fixed** - Two-phase streaming approach eliminates async context errors

### Performance
- **~~LLM Service Timeouts~~**: ✅ **Fixed with 180s streaming timeout**
- **Response Times**: Some endpoints slower than optimal during model warmup
- **Memory Usage**: Monitor memory consumption with enhanced features
- **Streaming Performance**: Real-time character-by-character display working optimally

---

## 📋 Development Notes

### Architecture Decisions
- **MCP Local Implementation**: Chose STDIO over HTTP for better local integration
- **XML Structured Prompts**: Enables rich UI rendering and thinking display
- **Single-Page Dashboard**: Simplified from tabs for better usability
- **Database Schema v2**: Enhanced to support advanced chat features
- **Tool Configuration**: Current hardcoded approach maintained while exploring UX for dynamic tool selection

### Technical Debt
- **CRITICAL: Traefik Routing Issue**: Gateway service not discoverable through Traefik proxy
  - Current: Frontend must use direct gateway (localhost:8000/api)
  - Target: Clean proxy URLs (localhost/api) for production parity
  - Impact: Dev/prod environment mismatch, hardcoded ports in frontend
- **Next.js Production Builds**: Currently configured for development mode only, needs production optimization
- **Provider Error Handling**: Need consistent error handling across all LLM providers
- **Test Coverage**: ✅ **Improved** - Added comprehensive conversation/auth tests, need provider/RAG coverage
- **Code Documentation**: Multi-provider architecture needs comprehensive documentation
- **Configuration Validation**: Limited validation of provider API keys and endpoints
- **Performance Monitoring**: No metrics collection for provider response times and costs

### Next Steps Priority
1. **Implement comprehensive test coverage** - Critical for maintainability
2. **Complete RAG integration** - Connect existing RAG service
3. **Production hardening** - Multi-provider security and error handling
4. **Next.js UI chat functionality** - Complete real-time chat features
5. **Performance optimization** - Provider response times and caching