# API Gateway Contract

This document defines the complete API contract for the PrivateGPT Gateway. It serves as the single source of truth for frontend developers building new UIs.

## Base Configuration

### Gateway URL
- **Development**: `http://localhost` (port 80 via Traefik)
- **Direct Gateway**: `http://localhost:8000` (bypasses Traefik)

### Authentication
All requests (except login) require JWT Bearer token in Authorization header:
```
Authorization: Bearer <jwt_token>
```

### Common Headers
```
Content-Type: application/json
Accept: application/json
```

### Error Response Format
```json
{
  "detail": "Error message",
  "status_code": 400,
  "error_code": "SPECIFIC_ERROR_CODE"
}
```

---

## Authentication Endpoints

### POST /api/auth/login
Login with email and password to get JWT tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name",
    "roles": ["user", "admin"]
  }
}
```

**Errors:**
- 401: Invalid credentials
- 422: Validation error

### POST /api/auth/refresh
Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### POST /api/auth/logout
Logout and invalidate tokens.

**Request:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200):**
```json
{
  "message": "Successfully logged out"
}
```

### GET /api/auth/profile
Get current user profile.

**Response (200):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "roles": ["user", "admin"],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

## Chat/LLM Endpoints

### GET /api/chat/conversations
Get all conversations for the current user.

**Query Parameters:**
- `limit` (int, default: 50): Number of conversations to return
- `offset` (int, default: 0): Pagination offset
- `search` (string, optional): Search in conversation titles

**Response (200):**
```json
{
  "conversations": [
    {
      "id": "conv_uuid",
      "title": "Contract Analysis Discussion",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "message_count": 15,
      "last_message_preview": "I've reviewed the contract and..."
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

### POST /api/chat/conversations
Create a new conversation.

**Request:**
```json
{
  "title": "New Conversation",
  "system_prompt": "You are a helpful assistant", // optional
  "initial_message": "Hello, I need help with..." // optional
}
```

**Response (201):**
```json
{
  "id": "conv_uuid",
  "title": "New Conversation",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "message_count": 0
}
```

### GET /api/chat/conversations/{conversation_id}
Get a specific conversation with messages.

**Response (200):**
```json
{
  "id": "conv_uuid",
  "title": "Contract Analysis Discussion",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "messages": [
    {
      "id": "msg_uuid",
      "role": "user",
      "content": "Can you analyze this contract?",
      "created_at": "2024-01-01T00:00:00Z",
      "attachments": []
    },
    {
      "id": "msg_uuid2",
      "role": "assistant",
      "content": "I'd be happy to analyze the contract...",
      "created_at": "2024-01-01T00:00:01Z",
      "tool_calls": []
    }
  ],
  "system_prompt": "You are a legal assistant"
}
```

### DELETE /api/chat/conversations/{conversation_id}
Delete a conversation.

**Response (204):** No content

### POST /api/chat/conversations/{conversation_id}/messages
Send a message and get streaming response.

**Request:**
```json
{
  "content": "Please analyze this employment contract",
  "attachments": ["doc_uuid1", "doc_uuid2"], // optional document IDs
  "stream": true, // optional, default: true
  "model": "gpt-4", // optional, uses default if not specified
  "temperature": 0.7, // optional
  "max_tokens": 2000 // optional
}
```

**Response (200) - Streaming:**
Server-Sent Events stream with the following event types:

```
event: message_start
data: {"id": "msg_uuid", "role": "assistant"}

event: content_delta
data: {"content": "I'll analyze"}

event: content_delta  
data: {"content": " the employment"}

event: tool_call_start
data: {"id": "tool_call_1", "type": "document_search", "function": {"name": "search_documents", "arguments": "{\"query\": \"employment law\"}"}}

event: tool_call_result
data: {"id": "tool_call_1", "result": "Found 3 relevant documents..."}

event: message_complete
data: {"id": "msg_uuid", "usage": {"prompt_tokens": 150, "completion_tokens": 450, "total_tokens": 600}}

event: error
data: {"error": "Rate limit exceeded", "code": "RATE_LIMIT"}
```

**Response (200) - Non-streaming:**
```json
{
  "id": "msg_uuid",
  "role": "assistant",
  "content": "I'll analyze the employment contract for you...",
  "created_at": "2024-01-01T00:00:00Z",
  "tool_calls": [
    {
      "id": "tool_call_1",
      "type": "function",
      "function": {
        "name": "search_documents",
        "arguments": "{\"query\": \"employment law\"}"
      },
      "result": "Found 3 relevant documents..."
    }
  ],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 450,
    "total_tokens": 600
  }
}
```

### GET /api/llm/models
Get available LLM models.

**Response (200):**
```json
{
  "models": [
    {
      "id": "gpt-4",
      "name": "GPT-4",
      "provider": "openai",
      "context_window": 8192,
      "max_output_tokens": 4096,
      "supports_functions": true,
      "supports_vision": true
    },
    {
      "id": "claude-3-opus",
      "name": "Claude 3 Opus",
      "provider": "anthropic",
      "context_window": 200000,
      "max_output_tokens": 4096,
      "supports_functions": true,
      "supports_vision": true
    }
  ],
  "default_model": "gpt-4"
}
```

### POST /api/llm/embeddings
Generate embeddings for text.

**Request:**
```json
{
  "text": "This is the text to embed",
  "model": "text-embedding-ada-002" // optional
}
```

**Response (200):**
```json
{
  "embedding": [0.0023, -0.0045, 0.0067, ...], // 1536 dimensions
  "model": "text-embedding-ada-002",
  "usage": {
    "prompt_tokens": 6,
    "total_tokens": 6
  }
}
```

---

## RAG (Document Management) Endpoints

### GET /api/rag/collections
Get all document collections.

**Query Parameters:**
- `include_deleted` (bool, default: false): Include soft-deleted collections
- `parent_id` (string, optional): Filter by parent collection

**Response (200):**
```json
[
  {
    "id": "coll_uuid",
    "name": "Legal Documents",
    "description": "Company legal documents",
    "icon": "📚",
    "color": "#6B7280",
    "collection_type": "collection",
    "parent_id": null,
    "path": "/Legal Documents",
    "document_count": 45,
    "total_document_count": 156,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "deleted_at": null,
    "children": [
      {
        "id": "coll_uuid2",
        "name": "Contracts",
        "collection_type": "folder",
        "parent_id": "coll_uuid",
        "path": "/Legal Documents/Contracts",
        "document_count": 111,
        "total_document_count": 111,
        "children": []
      }
    ]
  }
]
```

### POST /api/rag/collections
Create a new collection.

**Request:**
```json
{
  "name": "HR Policies",
  "description": "Human resources policy documents",
  "icon": "📋",
  "color": "#10B981",
  "parent_id": null,
  "collection_type": "collection" // or "folder"
}
```

**Response (201):**
```json
{
  "id": "coll_uuid",
  "name": "HR Policies",
  "description": "Human resources policy documents",
  "icon": "📋",
  "color": "#10B981",
  "collection_type": "collection",
  "parent_id": null,
  "path": "/HR Policies",
  "document_count": 0,
  "total_document_count": 0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### PATCH /api/rag/collections/{collection_id}
Update a collection.

**Request:**
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "icon": "📂",
  "color": "#F59E0B"
}
```

**Response (200):** Updated collection object

### DELETE /api/rag/collections/{collection_id}
Delete a collection.

**Query Parameters:**
- `hard_delete` (bool, default: false): Permanently delete instead of soft delete

**Response (204):** No content

### POST /api/rag/documents/upload
Upload a document (Phase 1 of 2-phase upload).

**Request:** Multipart form data
- `file`: The document file (PDF, TXT, MD, DOC, DOCX, XLS, XLSX)
- `collection_id`: UUID of the target collection

**Response (201):**
```json
{
  "upload_id": "upload_uuid",
  "file_name": "contract.pdf",
  "file_size": 2457600,
  "mime_type": "application/pdf",
  "status": "uploaded",
  "upload_url": "/api/rag/uploads/upload_uuid"
}
```

### POST /api/rag/documents
Create document record and start processing (Phase 2).

**Request:**
```json
{
  "upload_id": "upload_uuid",
  "collection_id": "coll_uuid",
  "title": "Employment Contract 2024",
  "description": "Standard employment contract template",
  "metadata": {
    "author": "Legal Team",
    "version": "2.0",
    "tags": ["employment", "legal", "template"]
  }
}
```

**Response (201):**
```json
{
  "id": "doc_uuid",
  "title": "Employment Contract 2024",
  "file_name": "contract.pdf",
  "file_size": 2457600,
  "mime_type": "application/pdf",
  "collection_id": "coll_uuid",
  "status": "processing",
  "processing_progress": {
    "stage": "splitting",
    "percentage": 0
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### GET /api/rag/documents/{document_id}
Get document details.

**Response (200):**
```json
{
  "id": "doc_uuid",
  "title": "Employment Contract 2024",
  "file_name": "contract.pdf",
  "file_size": 2457600,
  "mime_type": "application/pdf",
  "collection_id": "coll_uuid",
  "status": "complete",
  "chunk_count": 45,
  "processing_progress": {
    "stage": "complete",
    "percentage": 100
  },
  "metadata": {
    "author": "Legal Team",
    "version": "2.0",
    "tags": ["employment", "legal", "template"]
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "processed_at": "2024-01-01T00:05:00Z"
}
```

### GET /api/rag/documents
List documents in a collection.

**Query Parameters:**
- `collection_id` (string, required): Collection UUID
- `status` (string, optional): Filter by status (pending, processing, complete, failed)
- `limit` (int, default: 50)
- `offset` (int, default: 0)

**Response (200):**
```json
{
  "documents": [
    {
      "id": "doc_uuid",
      "title": "Employment Contract 2024",
      "file_name": "contract.pdf",
      "file_size": 2457600,
      "mime_type": "application/pdf",
      "status": "complete",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 45,
  "limit": 50,
  "offset": 0
}
```

### DELETE /api/rag/documents/{document_id}
Delete a document.

**Response (204):** No content

### GET /api/rag/documents/{document_id}/download
Download original document file.

**Response (200):** Binary file data with appropriate Content-Type header

### POST /api/rag/search
Search across documents.

**Request:**
```json
{
  "query": "employment termination clause",
  "collection_ids": ["coll_uuid1", "coll_uuid2"], // optional, searches all if not provided
  "limit": 10,
  "similarity_threshold": 0.7,
  "metadata_filters": {
    "tags": ["employment", "legal"]
  }
}
```

**Response (200):**
```json
{
  "results": [
    {
      "document_id": "doc_uuid",
      "document_title": "Employment Contract 2024",
      "chunk_id": "chunk_uuid",
      "content": "...the employment may be terminated by either party with 30 days written notice...",
      "similarity_score": 0.89,
      "metadata": {
        "page_number": 5,
        "section": "Termination"
      }
    }
  ],
  "total_results": 3,
  "query_embedding_time": 0.045,
  "search_time": 0.123
}
```

### GET /api/rag/documents/{document_id}/status
Get real-time processing status via SSE.

**Response:** Server-Sent Events stream
```
event: progress
data: {"stage": "splitting", "percentage": 25, "message": "Splitting document into chunks"}

event: progress
data: {"stage": "embedding", "percentage": 60, "message": "Generating embeddings for 45 chunks"}

event: complete
data: {"stage": "complete", "percentage": 100, "message": "Document processing complete", "chunk_count": 45}

event: error
data: {"stage": "failed", "error": "Unable to parse PDF", "code": "PARSE_ERROR"}
```

---

## WebSocket Endpoints

### WS /ws/chat/{conversation_id}
Real-time chat WebSocket connection.

**Connection URL:** `ws://localhost/ws/chat/{conversation_id}`

**Authentication:** Send token as first message after connection
```json
{
  "type": "auth",
  "token": "Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Message Types:**

User message:
```json
{
  "type": "message",
  "content": "What are the key terms in this contract?",
  "attachments": ["doc_uuid1"],
  "model": "gpt-4",
  "temperature": 0.7
}
```

Assistant response (streaming):
```json
{
  "type": "content_delta",
  "content": "I'll analyze"
}
```

Tool call:
```json
{
  "type": "tool_call",
  "id": "tool_1",
  "function": "search_documents",
  "arguments": {"query": "contract terms"}
}
```

Error:
```json
{
  "type": "error",
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT"
}
```

### WS /ws/documents/{document_id}/status
Real-time document processing status.

**Message Types:**
```json
{
  "type": "progress",
  "stage": "embedding",
  "percentage": 45,
  "chunks_processed": 20,
  "total_chunks": 45
}
```

---

## Admin Endpoints

### GET /api/admin/users
List all users (admin only).

**Query Parameters:**
- `limit` (int, default: 50)
- `offset` (int, default: 0)
- `search` (string, optional): Search in email/name

**Response (200):**
```json
{
  "users": [
    {
      "id": "user_uuid",
      "email": "user@example.com",
      "name": "User Name",
      "roles": ["user"],
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z",
      "last_login": "2024-01-15T00:00:00Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

### GET /api/admin/stats
Get system statistics (admin only).

**Response (200):**
```json
{
  "users": {
    "total": 150,
    "active_today": 45,
    "new_this_week": 12
  },
  "documents": {
    "total": 1250,
    "total_size_bytes": 5368709120,
    "processing": 3,
    "failed": 2
  },
  "conversations": {
    "total": 3400,
    "messages_total": 45600,
    "active_today": 89
  },
  "system": {
    "version": "1.0.0",
    "uptime_seconds": 864000,
    "vector_dimensions": 1536,
    "embedding_model": "text-embedding-ada-002"
  }
}
```

### POST /api/admin/reindex
Trigger document reindexing (admin only).

**Request:**
```json
{
  "collection_id": "coll_uuid", // optional, reindex all if not provided
  "force": false // force reindex even if already indexed
}
```

**Response (202):**
```json
{
  "job_id": "job_uuid",
  "status": "started",
  "estimated_documents": 450
}
```

---

## Rate Limiting

All endpoints are rate-limited per user:
- **Standard endpoints**: 100 requests per minute
- **Chat endpoints**: 20 requests per minute
- **Upload endpoints**: 10 requests per minute
- **Admin endpoints**: 50 requests per minute

Rate limit headers in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704067200
```

When rate limited, returns 429 status:
```json
{
  "detail": "Rate limit exceeded. Please wait 45 seconds.",
  "retry_after": 45
}
```

---

## Error Codes

Common error codes returned in responses:

- `INVALID_CREDENTIALS`: Invalid email or password
- `TOKEN_EXPIRED`: JWT token has expired
- `TOKEN_INVALID`: JWT token is invalid or malformed
- `UNAUTHORIZED`: Missing or invalid authorization
- `FORBIDDEN`: User lacks required permissions
- `NOT_FOUND`: Requested resource not found
- `VALIDATION_ERROR`: Request validation failed
- `RATE_LIMIT`: Rate limit exceeded
- `DOCUMENT_PARSE_ERROR`: Failed to parse uploaded document
- `EMBEDDING_ERROR`: Failed to generate embeddings
- `MODEL_NOT_AVAILABLE`: Requested model is not available
- `COLLECTION_NOT_EMPTY`: Cannot delete non-empty collection
- `STORAGE_FULL`: Storage quota exceeded
- `INTERNAL_ERROR`: Internal server error

---

## Best Practices

1. **Authentication**
   - Store tokens securely (httpOnly cookies or secure storage)
   - Refresh tokens before expiry (check `expires_in`)
   - Handle 401 responses by refreshing or re-authenticating

2. **Streaming Responses**
   - Use EventSource or similar for SSE endpoints
   - Handle connection drops and auto-reconnect
   - Process events incrementally for better UX

3. **File Uploads**
   - Show progress during upload
   - Validate file size/type client-side first
   - Use the 2-phase upload process correctly

4. **Error Handling**
   - Always check for error responses
   - Show user-friendly error messages
   - Log errors with correlation IDs

5. **Performance**
   - Cache collection lists (refresh periodically)
   - Paginate large result sets
   - Use WebSockets for real-time features

6. **Search**
   - Debounce search input (300-500ms)
   - Show loading states during search
   - Handle empty results gracefully