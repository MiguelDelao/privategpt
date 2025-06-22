# PrivateGPT Gateway API Contract

## Overview

This document serves as the definitive API contract between the PrivateGPT backend gateway service and any frontend implementation. It defines all endpoints, data models, authentication flows, streaming protocols, and integration patterns required to build a complete frontend experience.

**Gateway Base URL**: `http://localhost:8000` (development)

## Table of Contents

1. [Authentication & Authorization](#authentication--authorization)
2. [Chat & Conversations](#chat--conversations)
3. [Token Tracking & Usage Analytics](#token-tracking--usage-analytics)
4. [Model Management](#model-management)
5. [Tool Management](#tool-management)
6. [Document & RAG Management](#document--rag-management)
7. [Admin & Settings](#admin--settings)
8. [Real-time & Streaming](#real-time--streaming)
9. [Error Handling](#error-handling)
10. [Data Models](#data-models)
11. [Frontend Implementation Guidelines](#frontend-implementation-guidelines)

---

## Authentication & Authorization

### Authentication Flow

**Current Status**: Authentication is **temporarily disabled** for debugging and development. Most chat endpoints use a demo user (ID: 1) for testing. Auth can be re-enabled by removing the debug comments in `gateway/main.py`.

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "admin@admin.com",
  "password": "admin"
}
```

**Response (200)**:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "def50200...",
  "user": {
    "user_id": "uuid-string",
    "email": "admin@admin.com",
    "username": "admin",
    "first_name": "Admin",
    "last_name": "User",
    "roles": ["admin"],
    "primary_role": "admin"
  }
}
```

#### Token Verification
```http
POST /api/auth/verify
Authorization: Bearer {access_token}
```

**Response (200)**:
```json
{
  "valid": true,
  "user": {
    "user_id": "uuid-string",
    "email": "admin@admin.com",
    "username": "admin",
    "roles": ["admin"],
    "primary_role": "admin"
  }
}
```

#### Get Current User
```http
GET /api/auth/me
Authorization: Bearer {access_token}
```

**Response**: Same as token verification response.

### Frontend Authentication State Management

The frontend should maintain:
```typescript
interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  tokenExpiry: Date | null;
  refreshToken: string | null;
}
```

**Token Storage**: Store tokens in secure HTTP-only cookies or secure local storage. Include automatic refresh logic before token expiry.

---

## Chat & Conversations

### Core Chat Architecture

PrivateGPT uses a conversation-based chat system where:
- **Conversations** are persistent chat sessions with metadata and token tracking
- **Messages** belong to conversations and include rich content (text, tool calls, thinking) with individual token counts
- **Token Tracking** monitors usage at both message and conversation levels for analytics and billing
- **Context Management** enforces model context limits and provides clear error messages when exceeded
- **Streaming** is supported for real-time response generation
- **Tool Integration** allows AI to execute tools and display results

### Conversation Management

#### Create Conversation
```http
POST /api/chat/conversations
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "title": "New Chat",
  "model_name": "tinydolphin:latest",
  "system_prompt": "You are a helpful assistant.",
  "data": {
    "tags": ["work", "research"],
    "category": "general"
  }
}
```

**Response (201)**:
```json
{
  "id": "conv_uuid",
  "title": "New Chat",
  "status": "active",
  "model_name": "tinydolphin:latest",
  "system_prompt": "You are a helpful assistant.",
  "data": {
    "tags": ["work", "research"],
    "category": "general"
  },
  "created_at": "2024-12-20T10:30:00Z",
  "updated_at": "2024-12-20T10:30:00Z",
  "message_count": 0,
  "total_tokens": 0
}
```

#### List Conversations
```http
GET /api/chat/conversations?limit=50&offset=0&status=active
Authorization: Bearer {access_token}
```

**Query Parameters**:
- `limit`: Number of conversations to return (1-100, default: 50)
- `offset`: Pagination offset (default: 0)
- `status`: Filter by status (`active`, `archived`, `deleted`)
- `search`: Search in conversation titles
- `model_name`: Filter by model
- `created_after`: ISO date filter
- `created_before`: ISO date filter

**Response (200)**:
```json
[
  {
    "id": "conv_uuid",
    "title": "Chat about AI",
    "status": "active",
    "model_name": "tinydolphin:latest",
    "system_prompt": "You are a helpful assistant.",
    "data": {},
    "created_at": "2024-12-20T10:30:00Z",
    "updated_at": "2024-12-20T10:35:00Z",
    "message_count": 5,
    "total_tokens": 1250
  }
]
```

**Note**: Returns array directly. Pagination metadata not implemented in current version.

#### Get Conversation
```http
GET /api/chat/conversations/{conversation_id}
Authorization: Bearer {access_token}
```

**Response**: Same as create conversation response, plus messages array.

#### Update Conversation
```http
PATCH /api/chat/conversations/{conversation_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "title": "Updated Chat Title",
  "status": "archived",
  "data": {
    "tags": ["archived", "completed"]
  }
}
```

#### Delete Conversation
```http
DELETE /api/chat/conversations/{conversation_id}
Authorization: Bearer {access_token}
```

**Response (204)**: No content

---

## Token Tracking & Usage Analytics

### Overview

PrivateGPT implements comprehensive token tracking to monitor usage at both message and conversation levels. This enables usage analytics, billing, and context management.

### Key Features

- **Message-level token counting**: Each message stores its token count
- **Conversation-level aggregation**: Running total of all tokens used in a conversation
- **Context limit validation**: Prevents exceeding model context windows
- **Real-time token usage**: Returns actual token counts from LLM APIs
- **Provider-specific counting**: Uses appropriate tokenization for each LLM provider

### Token Information in Responses

All chat responses include detailed token usage information:

```json
{
  "conversation_id": "conv_uuid",
  "message": {
    "id": "msg_user_uuid",
    "conversation_id": "conv_uuid", 
    "role": "user",
    "content": "Hello! What can you help me with?",
    "token_count": 15,
    "created_at": "2024-12-20T10:40:00Z"
  },
  "response": {
    "id": "msg_assistant_uuid",
    "conversation_id": "conv_uuid",
    "role": "assistant", 
    "content": "Hello! I'm here to help you with a wide variety of tasks...",
    "token_count": 28,
    "data": {
      "model": "tinyllama:1.1b",
      "input_tokens": 15,
      "output_tokens": 28, 
      "total_tokens": 43,
      "response_time_ms": 1250
    },
    "created_at": "2024-12-20T10:40:03Z"
  }
}
```

### Context Limit Management

When a conversation approaches or exceeds the model's context limit, the API returns detailed error information:

#### Context Limit Exceeded Error (HTTP 413)
```json
{
  "detail": {
    "error": "context_limit_exceeded",
    "message": "Adding this message would exceed context limit. Current conversation: 3800 tokens, new message: 250 tokens, total would be 4050 tokens, but model tinyllama:1.1b only supports 4096 tokens.",
    "current_tokens": 3800,
    "limit": 4096,
    "model_name": "tinyllama:1.1b",
    "suggestions": [
      "Start a new conversation",
      "Use a model with larger context (current: 4096 tokens)",
      "Shorten your message"
    ]
  }
}
```

### Token Tracking in Conversations

Conversations maintain a running total of all tokens used:

```json
{
  "id": "conv_uuid",
  "title": "AI Discussion",
  "status": "active",
  "model_name": "tinyllama:1.1b",
  "total_tokens": 1547,
  "message_count": 12,
  "created_at": "2024-12-20T10:30:00Z",
  "updated_at": "2024-12-20T10:45:00Z"
}
```

### Debug Endpoints (Development Only)

For testing and debugging token tracking:

#### Test Token Tracking
```http
GET /test-token-system/{conversation_id}
```

**Response (200)**:
```json
{
  "success": true,
  "conversation_id": "conv_uuid",
  "user_tokens": 15,
  "assistant_tokens": 28,
  "assistant_content": "Hello! I'm here to help you..."
}
```

---

### Message Management

#### List Messages
```http
GET /api/chat/conversations/{conversation_id}/messages?limit=100&offset=0
Authorization: Bearer {access_token}
```

**Query Parameters**:
- `limit`: Messages per page (1-200, default: 100)
- `offset`: Pagination offset
- `role`: Filter by role (`user`, `assistant`, `system`, `tool`)
- `created_after`: ISO date filter
- `include_tool_calls`: Include tool call details (default: true)
- `include_thinking`: Include thinking content (default: true)

**Response (200)**:
```json
[
  {
    "id": "msg_uuid",
    "conversation_id": "conv_uuid",
    "role": "user",
    "content": "What is machine learning?",
    "raw_content": null,
    "token_count": 15,
    "data": {},
    "created_at": "2024-12-20T10:30:00Z",
    "updated_at": "2024-12-20T10:30:00Z"
  },
  {
    "id": "msg_uuid_2",
    "conversation_id": "conv_uuid",
    "role": "assistant", 
    "content": "Machine learning is a subset of artificial intelligence...",
    "raw_content": null,
    "token_count": 150,
    "data": {
      "model": "tinyllama:1.1b",
      "input_tokens": 15,
      "output_tokens": 150,
      "total_tokens": 165,
      "response_time_ms": 1250
    },
    "created_at": "2024-12-20T10:30:05Z",
    "updated_at": "2024-12-20T10:30:05Z"
  }
]
```

**Note**: Returns array directly. Tool calls and thinking content not yet implemented in current version.

### Direct Chat (Stateless)

For quick interactions without conversation persistence:

#### Direct Chat
```http
POST /api/chat/direct
Content-Type: application/json

{
  "message": "Hello, how are you?",
  "model": "tinydolphin:latest",
  "temperature": 0.7,
  "max_tokens": 500,
  "use_mcp": false,
  "available_tools": ""
}
```

#### Direct Chat Streaming
```http
POST /api/chat/direct/stream
Content-Type: application/json
Accept: text/event-stream

{
  "message": "Hello, how are you?",
  "model": "tinydolphin:latest",
  "temperature": 0.7,
  "max_tokens": 500,
  "use_mcp": false,
  "available_tools": ""
}
```

**Response (200)**:
```json
{
  "text": "Hello! I'm doing well, thank you for asking. How can I help you today?",
  "model": "tinyllama:1.1b",
  "response_time_ms": 1250.5,
  "tools_used": false
}
```

**Note**: Direct chat responses in current implementation don't include token counts. Use conversation chat for token tracking.

#### MCP Chat (With Tools)
```http
POST /api/chat/mcp
Content-Type: application/json

{
  "message": "Search for documents about machine learning",
  "model": "tinydolphin:latest",
  "temperature": 0.7,
  "max_tokens": 500,
  "use_mcp": true,
  "available_tools": "*"
}
```

#### MCP Chat Streaming
```http
POST /api/chat/mcp/stream
Content-Type: application/json
Accept: text/event-stream

{
  "message": "Search for documents about machine learning",
  "model": "tinydolphin:latest",
  "temperature": 0.7,
  "max_tokens": 500,
  "use_mcp": true,
  "available_tools": "*"
}
```

**Response (200)**:
```json
{
  "text": "I found several documents about machine learning in your knowledge base...",
  "model": "tinydolphin:latest",
  "response_time_ms": 2150.8,
  "tools_used": true,
  "tool_calls": [
    {
      "tool_name": "search_documents",
      "arguments": {
        "query": "machine learning",
        "limit": 5
      },
      "result": "{\n  \"results\": [...]\n}",
      "success": true,
      "execution_time_ms": 450
    }
  ],
  "token_count": {
    "input": 25,
    "output": 85
  }
}
```

### Conversation Chat (Persistent)

#### Send Message to Conversation
```http
POST /api/chat/conversations/{conversation_id}/chat
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "message": "Explain quantum computing",
  "stream": false,
  "model_name": "tinydolphin:latest",
  "temperature": 0.8,
  "max_tokens": 1000,
  "use_mcp": true,
  "available_tools": "search_documents,rag_chat"
}
```

**Response (200)**:
```json
{
  "conversation_id": "conv_uuid",
  "message": {
    "id": "msg_user_uuid",
    "conversation_id": "conv_uuid",
    "role": "user",
    "content": "Explain quantum computing",
    "raw_content": null,
    "token_count": 25,
    "data": {},
    "created_at": "2024-12-20T10:40:00Z",
    "updated_at": "2024-12-20T10:40:00Z"
  },
  "response": {
    "id": "msg_assistant_uuid",
    "conversation_id": "conv_uuid",
    "role": "assistant",
    "content": "Quantum computing is a revolutionary computing paradigm...",
    "raw_content": null,
    "token_count": 185,
    "data": {
      "model": "tinyllama:1.1b",
      "input_tokens": 25,
      "output_tokens": 185,
      "total_tokens": 210
    },
    "created_at": "2024-12-20T10:40:03Z",
    "updated_at": "2024-12-20T10:40:03Z"
  }
}
```

---

## Real-time & Streaming

### Server-Sent Events (SSE) Protocol

For real-time chat responses, use SSE streaming:

#### Stream Conversation Chat
```http
POST /api/chat/conversations/{conversation_id}/chat/stream
Authorization: Bearer {access_token}
Content-Type: application/json
Accept: text/event-stream

{
  "message": "Write a story about AI",
  "model_name": "tinydolphin:latest",
  "temperature": 0.9,
  "max_tokens": 2000,
  "use_mcp": true,
  "available_tools": "*"
}
```

**Response (200)**:
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"type": "conversation_start", "conversation_id": "conv_uuid", "message_id": "msg_uuid"}

data: {"type": "thinking_start"}

data: {"type": "thinking_content", "content": "The user wants me to write a creative story about AI..."}

data: {"type": "thinking_end"}

data: {"type": "tool_call_start", "tool_name": "search_documents", "tool_call_id": "tool_uuid"}

data: {"type": "tool_call_end", "tool_call_id": "tool_uuid", "success": true, "result": "{\"results\": [...]}"}

data: {"type": "content_start"}

data: {"type": "content_delta", "content": "Once"}

data: {"type": "content_delta", "content": " upon"}

data: {"type": "content_delta", "content": " a"}

data: {"type": "content_delta", "content": " time"}

data: {"type": "content_delta", "content": ","}

data: {"type": "content_delta", "content": " in"}

data: {"type": "content_delta", "content": " a"}

data: {"type": "content_delta", "content": " world"}

data: {"type": "content_end"}

data: {"type": "message_complete", "message": {"id": "msg_uuid", "conversation_id": "conv_uuid", "role": "assistant", "content": "Once upon a time, in a world...", "token_count": 245, "response_time_ms": 3500}}

data: {"type": "done"}
```

### Streaming Event Types

| Event Type | Description | Data Fields |
|------------|-------------|-------------|
| `conversation_start` | Chat session begins | `conversation_id`, `message_id` |
| `thinking_start` | AI begins reasoning | None |
| `thinking_content` | AI reasoning content | `content` |
| `thinking_end` | AI reasoning complete | None |
| `tool_call_start` | Tool execution begins | `tool_name`, `tool_call_id`, `arguments` |
| `tool_call_end` | Tool execution complete | `tool_call_id`, `success`, `result`, `error?` |
| `content_start` | Response generation begins | None |
| `content_delta` | Incremental response content | `content` |
| `content_end` | Response generation complete | None |
| `message_complete` | Full message with metadata | Complete `message` object |
| `error` | Error occurred | `error`, `message` |
| `done` | Stream complete | None |

### Frontend Streaming Implementation

```typescript
interface StreamEvent {
  type: string;
  [key: string]: any;
}

class ChatStreamer {
  private eventSource: EventSource;
  
  streamChat(conversationId: string, message: ChatMessage): Promise<Message> {
    return new Promise((resolve, reject) => {
      const url = `/api/chat/conversations/${conversationId}/chat/stream`;
      
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream'
        },
        body: JSON.stringify(message)
      })
      .then(response => {
        const reader = response.body.getReader();
        
        const processStream = () => {
          return reader.read().then(({ done, value }) => {
            if (done) return;
            
            const chunk = new TextDecoder().decode(value);
            const lines = chunk.split('\n');
            
            lines.forEach(line => {
              if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));
                this.handleStreamEvent(data);
              }
            });
            
            return processStream();
          });
        };
        
        return processStream();
      });
    });
  }
  
  private handleStreamEvent(event: StreamEvent) {
    switch (event.type) {
      case 'thinking_content':
        this.onThinkingUpdate(event.content);
        break;
      case 'content_delta':
        this.onContentDelta(event.content);
        break;
      case 'tool_call_start':
        this.onToolCallStart(event);
        break;
      case 'message_complete':
        this.onMessageComplete(event.message);
        break;
      // ... handle other events
    }
  }
}
```

---

## Model Management

### List Available Models
```http
GET /api/llm/models
```

**Response (200)**:
```json
[
  {
    "name": "tinydolphin:latest",
    "size": 636743607,
    "modified_at": "2024-12-19T10:03:12Z",
    "family": "llama",
    "parameter_size": "1B",
    "quantization": "Q4_0",
    "capabilities": {
      "chat": true,
      "completion": true,
      "function_calling": true,
      "streaming": true
    },
    "memory_requirements": {
      "minimum_gb": 0.8,
      "recommended_gb": 1.2
    },
    "performance": {
      "tokens_per_second": 45,
      "latency_ms": 150
    }
  },
  {
    "name": "llama3.2:1b",
    "size": 1321098329,
    "modified_at": "2024-12-19T17:34:40Z",
    "family": "llama",
    "parameter_size": "1.2B",
    "quantization": "Q8_0",
    "capabilities": {
      "chat": true,
      "completion": true,
      "function_calling": true,
      "streaming": true
    },
    "memory_requirements": {
      "minimum_gb": 2.1,
      "recommended_gb": 2.5
    },
    "performance": {
      "tokens_per_second": 35,
      "latency_ms": 200
    },
    "status": "insufficient_memory"
  }
]
```

### Model Health Check
```http
GET /api/llm/health
```

**Response (200)**:
```json
{
  "status": "healthy",
  "service": "llm",
  "models_loaded": ["tinydolphin:latest"],
  "memory_usage": {
    "total_gb": 2.0,
    "used_gb": 1.2,
    "available_gb": 0.8
  },
  "performance": {
    "avg_response_time_ms": 175,
    "requests_per_minute": 25
  }
}
```

---

## Tool Management

### List Available Tools
```http
GET /api/tools/available
Authorization: Bearer {access_token}
```

**Response (200)**:
```json
{
  "tools": [
    {
      "name": "search_documents",
      "display_name": "Search Documents",
      "description": "Search through uploaded documents using semantic similarity",
      "category": "rag",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "The search query"
          },
          "limit": {
            "type": "integer",
            "description": "Maximum number of results",
            "default": 10,
            "minimum": 1,
            "maximum": 50
          },
          "include_sources": {
            "type": "boolean",
            "description": "Include source document information",
            "default": true
          }
        },
        "required": ["query"]
      },
      "enabled": true,
      "permissions": ["user", "admin"]
    },
    {
      "name": "rag_chat",
      "display_name": "RAG Chat",
      "description": "Ask questions using RAG with document context",
      "category": "rag",
      "parameters": {
        "type": "object",
        "properties": {
          "question": {
            "type": "string",
            "description": "The question to ask"
          },
          "conversation_context": {
            "type": "string",
            "description": "Optional previous conversation context"
          }
        },
        "required": ["question"]
      },
      "enabled": true,
      "permissions": ["user", "admin"]
    },
    {
      "name": "create_file",
      "display_name": "Create File",
      "description": "Create a new file with specified content",
      "category": "file_operations",
      "parameters": {
        "type": "object",
        "properties": {
          "file_path": {
            "type": "string",
            "description": "Path where the file should be created"
          },
          "content": {
            "type": "string",
            "description": "Content to write to the file"
          },
          "encoding": {
            "type": "string",
            "description": "File encoding",
            "default": "utf-8"
          }
        },
        "required": ["file_path", "content"]
      },
      "enabled": true,
      "permissions": ["admin"]
    },
    {
      "name": "read_file",
      "display_name": "Read File",
      "description": "Read the contents of a file",
      "category": "file_operations",
      "parameters": {
        "type": "object",
        "properties": {
          "file_path": {
            "type": "string",
            "description": "Path to the file to read"
          },
          "encoding": {
            "type": "string",
            "description": "File encoding",
            "default": "utf-8"
          },
          "max_lines": {
            "type": "integer",
            "description": "Maximum number of lines to read"
          }
        },
        "required": ["file_path"]
      },
      "enabled": true,
      "permissions": ["user", "admin"]
    },
    {
      "name": "get_system_info",
      "display_name": "Get System Info",
      "description": "Get basic system information and resource usage",
      "category": "system",
      "parameters": {
        "type": "object",
        "properties": {},
        "required": []
      },
      "enabled": true,
      "permissions": ["admin"]
    },
    {
      "name": "check_service_health",
      "display_name": "Check Service Health",
      "description": "Check the health status of all PrivateGPT services",
      "category": "system",
      "parameters": {
        "type": "object",
        "properties": {},
        "required": []
      },
      "enabled": true,
      "permissions": ["admin"]
    }
  ],
  "categories": [
    {
      "name": "rag",
      "display_name": "Document & RAG",
      "description": "Tools for document search and retrieval-augmented generation",
      "icon": "📚"
    },
    {
      "name": "file_operations",
      "display_name": "File Operations",
      "description": "Tools for file management and manipulation",
      "icon": "📁"
    },
    {
      "name": "system",
      "display_name": "System Information",
      "description": "Tools for system monitoring and health checks",
      "icon": "⚙️"
    }
  ]
}
```

### Tool Usage Analytics
```http
GET /api/tools/analytics?period=7d
Authorization: Bearer {access_token}
```

**Response (200)**:
```json
{
  "period": "7d",
  "total_executions": 1250,
  "tools": [
    {
      "name": "search_documents",
      "executions": 890,
      "success_rate": 0.98,
      "avg_execution_time_ms": 245,
      "total_execution_time_ms": 218050
    },
    {
      "name": "rag_chat",
      "executions": 245,
      "success_rate": 0.96,
      "avg_execution_time_ms": 1250,
      "total_execution_time_ms": 306250
    }
  ]
}
```

---

## Document & RAG Management

### Upload Document
```http
POST /api/rag/documents
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

Form fields:
- file: [file data]
- title: "Optional custom title"
- metadata: {"source": "research", "category": "ai"}
```

**Response (201)**:
```json
{
  "id": "doc_uuid",
  "title": "AI Research Paper.pdf",
  "filename": "ai_research_paper.pdf",
  "size_bytes": 1048576,
  "content_type": "application/pdf",
  "status": "processing",
  "metadata": {
    "source": "research",
    "category": "ai",
    "uploaded_by": "user@example.com"
  },
  "created_at": "2024-12-20T11:00:00Z",
  "processing": {
    "estimated_completion": "2024-12-20T11:02:00Z",
    "progress": 0
  }
}
```

### List Documents
```http
GET /api/rag/documents?limit=50&offset=0&status=processed&search=AI
Authorization: Bearer {access_token}
```

**Query Parameters**:
- `limit`: Documents per page (1-100, default: 50)
- `offset`: Pagination offset
- `status`: Filter by status (`uploading`, `processing`, `processed`, `failed`)
- `search`: Search in titles and content
- `category`: Filter by metadata category
- `uploaded_after`: ISO date filter
- `uploaded_before`: ISO date filter

**Response (200)**:
```json
{
  "documents": [
    {
      "id": "doc_uuid",
      "title": "AI Research Paper.pdf",
      "filename": "ai_research_paper.pdf",
      "size_bytes": 1048576,
      "content_type": "application/pdf",
      "status": "processed",
      "metadata": {
        "source": "research",
        "category": "ai",
        "uploaded_by": "user@example.com",
        "page_count": 25,
        "word_count": 8500
      },
      "created_at": "2024-12-20T11:00:00Z",
      "processed_at": "2024-12-20T11:01:45Z",
      "chunks": {
        "total": 45,
        "embedded": 45
      },
      "processing_time_ms": 105000
    }
  ],
  "total": 125,
  "has_more": true,
  "aggregations": {
    "by_status": {
      "processed": 120,
      "processing": 3,
      "failed": 2
    },
    "by_category": {
      "ai": 45,
      "research": 30,
      "documentation": 25,
      "other": 25
    }
  }
}
```

### Get Document
```http
GET /api/rag/documents/{document_id}
Authorization: Bearer {access_token}
```

**Response (200)**:
```json
{
  "id": "doc_uuid",
  "title": "AI Research Paper.pdf",
  "filename": "ai_research_paper.pdf",
  "size_bytes": 1048576,
  "content_type": "application/pdf",
  "status": "processed",
  "metadata": {
    "source": "research",
    "category": "ai",
    "uploaded_by": "user@example.com",
    "page_count": 25,
    "word_count": 8500,
    "language": "en",
    "extracted_entities": ["machine learning", "neural networks", "deep learning"]
  },
  "created_at": "2024-12-20T11:00:00Z",
  "processed_at": "2024-12-20T11:01:45Z",
  "chunks": [
    {
      "id": "chunk_uuid_1",
      "content": "Machine learning is a subset of artificial intelligence...",
      "page": 1,
      "position": 0,
      "token_count": 125,
      "embedding_model": "BAAI/bge-small-en-v1.5"
    }
  ],
  "processing_time_ms": 105000,
  "download_url": "/api/rag/documents/doc_uuid/download"
}
```

### Search Documents
```http
POST /api/rag/search
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "query": "machine learning algorithms",
  "limit": 10,
  "include_metadata": true,
  "filters": {
    "category": ["ai", "research"],
    "uploaded_after": "2024-01-01T00:00:00Z"
  },
  "similarity_threshold": 0.7
}
```

**Response (200)**:
```json
{
  "query": "machine learning algorithms",
  "results": [
    {
      "chunk_id": "chunk_uuid_1",
      "document_id": "doc_uuid",
      "document_title": "AI Research Paper.pdf",
      "content": "Machine learning algorithms are computational methods that enable computers to learn patterns...",
      "similarity_score": 0.92,
      "page": 3,
      "position": 1,
      "metadata": {
        "category": "ai",
        "source": "research"
      }
    }
  ],
  "total_found": 25,
  "search_time_ms": 150,
  "filters_applied": {
    "category": ["ai", "research"],
    "uploaded_after": "2024-01-01T00:00:00Z"
  }
}
```

### Delete Document
```http
DELETE /api/rag/documents/{document_id}
Authorization: Bearer {access_token}
```

**Response (204)**: No content

### RAG Chat
```http
POST /api/rag/chat
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "question": "What are the latest developments in neural networks?",
  "context": "Previous conversation about AI...",
  "document_filters": {
    "category": ["ai", "research"],
    "uploaded_after": "2024-01-01T00:00:00Z"
  },
  "max_documents": 5,
  "include_citations": true
}
```

**Response (200)**:
```json
{
  "question": "What are the latest developments in neural networks?",
  "answer": "Based on the recent research in your documents, there have been several significant developments in neural networks...",
  "sources": [
    {
      "document_id": "doc_uuid_1",
      "document_title": "Neural Networks 2024 Survey",
      "chunk_id": "chunk_uuid_1",
      "content": "Recent advances in transformer architectures...",
      "similarity_score": 0.95,
      "page": 5
    }
  ],
  "confidence": 0.89,
  "response_time_ms": 1850,
  "documents_searched": 45,
  "chunks_retrieved": 8
}
```

---

## Admin & Settings

### Get System Settings
```http
GET /api/admin/settings
Authorization: Bearer {access_token}
```

**Response (200)**:
```json
{
  "system": {
    "app_title": "PrivateGPT",
    "app_subtitle": "Your Secure, Self-Hosted AI Assistant",
    "version": "2.0.0",
    "environment": "development",
    "debug_mode": true
  },
  "authentication": {
    "provider": "keycloak",
    "keycloak_url": "http://keycloak:8180",
    "realm": "privategpt",
    "client_id": "privategpt-ui",
    "session_timeout_minutes": 60,
    "require_email_verification": false
  },
  "llm": {
    "provider": "ollama",
    "base_url": "http://ollama:11434",
    "default_model": "tinyllama:1.1b",
    "max_tokens": 2000,
    "temperature": 0.7,
    "timeout_seconds": 180,
    "recommended_models": [
      "tinyllama:1.1b",
      "gemma2:2b",
      "phi3:mini"
    ],
    "note": "Use lighter models like tinyllama:1.1b for development due to memory constraints"
  },
  "rag": {
    "embedding_model": "BAAI/bge-small-en-v1.5",
    "chunk_size": 512,
    "chunk_overlap": 50,
    "similarity_threshold": 0.7,
    "max_documents_per_query": 5,
    "supported_file_types": [".pdf", ".txt", ".docx", ".md"],
    "max_file_size_mb": 50
  },
  "mcp": {
    "enabled": true,
    "transport": "stdio",
    "available_tools": "*",
    "tool_timeout_seconds": 30
  },
  "ui": {
    "theme": "light",
    "language": "en",
    "enable_thinking_display": true,
    "enable_tool_calls_display": true,
    "enable_streaming": true,
    "default_conversation_title": "New Chat"
  },
  "limits": {
    "max_conversations_per_user": 100,
    "max_messages_per_conversation": 1000,
    "max_documents_per_user": 50,
    "rate_limit_requests_per_minute": 60
  }
}
```

### Update System Settings
```http
PATCH /api/admin/settings
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "llm": {
    "default_model": "llama3.2:1b",
    "temperature": 0.8
  },
  "ui": {
    "theme": "dark",
    "enable_thinking_display": false
  }
}
```

**Response (200)**:
```json
{
  "updated_settings": {
    "llm.default_model": "llama3.2:1b",
    "llm.temperature": 0.8,
    "ui.theme": "dark",
    "ui.enable_thinking_display": false
  },
  "validation_errors": [],
  "restart_required": false,
  "updated_at": "2024-12-20T12:00:00Z"
}
```

### System Health
```http
GET /api/admin/health
Authorization: Bearer {access_token}
```

**Response (200)**:
```json
{
  "overall_status": "healthy",
  "services": {
    "gateway": {
      "status": "healthy",
      "response_time_ms": 5,
      "uptime_seconds": 86400,
      "memory_usage_mb": 150,
      "cpu_usage_percent": 2.5
    },
    "llm": {
      "status": "healthy",
      "response_time_ms": 45,
      "models_loaded": ["tinydolphin:latest"],
      "memory_usage_mb": 1200,
      "cpu_usage_percent": 15.2
    },
    "rag": {
      "status": "healthy",
      "response_time_ms": 25,
      "documents_indexed": 125,
      "chunks_indexed": 5678,
      "memory_usage_mb": 300,
      "cpu_usage_percent": 5.1
    },
    "database": {
      "status": "healthy",
      "response_time_ms": 8,
      "connections_active": 5,
      "connections_max": 20,
      "storage_used_gb": 2.5,
      "storage_available_gb": 47.5
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 2,
      "memory_usage_mb": 50,
      "connected_clients": 3,
      "keys_total": 245
    }
  },
  "system": {
    "cpu_cores": 8,
    "memory_total_gb": 16,
    "memory_used_gb": 8.5,
    "disk_total_gb": 500,
    "disk_used_gb": 125,
    "load_average": [1.2, 1.1, 1.0]
  },
  "checked_at": "2024-12-20T12:05:00Z"
}
```

### User Management
```http
GET /api/admin/users?limit=50&offset=0&role=user&search=john
Authorization: Bearer {access_token}
```

**Response (200)**:
```json
{
  "users": [
    {
      "id": "user_uuid",
      "email": "john.doe@example.com",
      "username": "john.doe",
      "first_name": "John",
      "last_name": "Doe",
      "roles": ["user"],
      "status": "active",
      "created_at": "2024-12-01T10:00:00Z",
      "last_login": "2024-12-20T09:30:00Z",
      "stats": {
        "conversations": 25,
        "messages": 450,
        "documents_uploaded": 12,
        "total_tokens_used": 125000
      }
    }
  ],
  "total": 156,
  "has_more": true
}
```

---

## Error Handling

### Standard Error Response Format

All API errors follow this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "field": "email",
      "reason": "Invalid email format",
      "provided_value": "invalid-email"
    },
    "request_id": "req_uuid",
    "timestamp": "2024-12-20T12:10:00Z"
  }
}
```

### HTTP Status Codes

| Code | Description | Usage |
|------|-------------|-------|
| `200` | OK | Successful GET, PATCH requests |
| `201` | Created | Successful POST requests |
| `204` | No Content | Successful DELETE requests |
| `400` | Bad Request | Invalid request format, validation errors |
| `401` | Unauthorized | Missing or invalid authentication |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource doesn't exist |
| `409` | Conflict | Resource already exists, state conflict |
| `413` | Payload Too Large | File upload size exceeded |
| `422` | Unprocessable Entity | Valid format but business logic error |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Unexpected server error |
| `502` | Bad Gateway | Downstream service error |
| `503` | Service Unavailable | Service temporarily unavailable |

### Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Request validation failed |
| `AUTHENTICATION_REQUIRED` | Authentication required |
| `AUTHORIZATION_FAILED` | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | Requested resource not found |
| `RESOURCE_CONFLICT` | Resource already exists |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `FILE_TOO_LARGE` | File size exceeds limit |
| `UNSUPPORTED_FILE_TYPE` | File type not supported |
| `PROCESSING_FAILED` | Document processing failed |
| `MODEL_UNAVAILABLE` | LLM model not available |
| `CONTEXT_LIMIT_EXCEEDED` | Conversation exceeds model context limit |
| `TOOL_EXECUTION_FAILED` | MCP tool execution failed |
| `SERVICE_UNAVAILABLE` | Backend service unavailable |
| `QUOTA_EXCEEDED` | Usage quota exceeded |

---

## Data Models

### Core Types

```typescript
interface User {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  roles: string[];
  primary_role: string;
  status: 'active' | 'inactive' | 'suspended';
  created_at: string;
  last_login?: string;
}

interface Conversation {
  id: string;
  title: string;
  status: 'active' | 'archived' | 'deleted';
  model_name?: string;
  system_prompt?: string;
  data: Record<string, any>;
  created_at: string;
  updated_at: string;
  message_count: number;
  total_tokens: number;
  last_message_at?: string;
  preview?: string;
}

interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  raw_content?: string;
  thinking_content?: string;
  token_count?: number;
  tool_calls?: ToolCall[];
  data: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface ToolCall {
  id: string;
  tool_name: string;
  arguments: Record<string, any>;
  result?: string;
  success: boolean;
  execution_time_ms: number;
  error?: string;
}

interface Model {
  name: string;
  size: number;
  modified_at: string;
  family: string;
  parameter_size: string;
  quantization: string;
  capabilities: {
    chat: boolean;
    completion: boolean;
    function_calling: boolean;
    streaming: boolean;
  };
  memory_requirements: {
    minimum_gb: number;
    recommended_gb: number;
  };
  performance: {
    tokens_per_second: number;
    latency_ms: number;
  };
  status?: 'available' | 'insufficient_memory' | 'loading' | 'error';
}

interface Tool {
  name: string;
  display_name: string;
  description: string;
  category: string;
  parameters: {
    type: 'object';
    properties: Record<string, any>;
    required: string[];
  };
  enabled: boolean;
  permissions: string[];
}

interface Document {
  id: string;
  title: string;
  filename: string;
  size_bytes: number;
  content_type: string;
  status: 'uploading' | 'processing' | 'processed' | 'failed';
  metadata: Record<string, any>;
  created_at: string;
  processed_at?: string;
  chunks?: {
    total: number;
    embedded: number;
  };
  processing_time_ms?: number;
  download_url?: string;
}

interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_title: string;
  content: string;
  similarity_score: number;
  page?: number;
  position?: number;
  metadata: Record<string, any>;
}
```

---

## Frontend Implementation Guidelines

### Authentication State Management

```typescript
// React/Redux example
interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  tokenExpiry: Date | null;
  refreshToken: string | null;
  isLoading: boolean;
  error: string | null;
}

// Actions
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    loginStart: (state) => {
      state.isLoading = true;
      state.error = null;
    },
    loginSuccess: (state, action) => {
      state.isAuthenticated = true;
      state.user = action.payload.user;
      state.token = action.payload.access_token;
      state.tokenExpiry = new Date(Date.now() + action.payload.expires_in * 1000);
      state.refreshToken = action.payload.refresh_token;
      state.isLoading = false;
    },
    loginFailure: (state, action) => {
      state.isAuthenticated = false;
      state.user = null;
      state.token = null;
      state.error = action.payload;
      state.isLoading = false;
    },
    logout: (state) => {
      state.isAuthenticated = false;
      state.user = null;
      state.token = null;
      state.refreshToken = null;
      state.tokenExpiry = null;
    }
  }
});
```

### HTTP Client Configuration

```typescript
// Axios interceptor example
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000
});

// Request interceptor for auth
apiClient.interceptors.request.use((config) => {
  const token = store.getState().auth.token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      store.dispatch(logout());
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### Chat State Management

```typescript
interface ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Record<string, Message[]>; // conversationId -> messages
  isStreaming: boolean;
  streamingMessage: Partial<Message> | null;
  isLoading: boolean;
  error: string | null;
}

// Real-time message updates
const handleStreamEvent = (event: StreamEvent) => {
  switch (event.type) {
    case 'content_delta':
      updateStreamingMessage(event.content);
      break;
    case 'thinking_content':
      updateThinkingContent(event.content);
      break;
    case 'tool_call_start':
      addToolCallStatus(event);
      break;
    case 'message_complete':
      finalizeMessage(event.message);
      break;
  }
};
```

### Error Boundary Implementation

```typescript
interface ErrorInfo {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
  request_id?: string;
}

class APIErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log to monitoring service
    console.error('API Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} />;
    }
    return this.props.children;
  }
}
```

### Performance Considerations

1. **Pagination**: Always implement pagination for lists
2. **Debouncing**: Debounce search inputs (300ms recommended)
3. **Memoization**: Use React.memo for expensive components
4. **Virtual Scrolling**: For large message lists
5. **Lazy Loading**: Load conversations and documents on demand
6. **Caching**: Cache frequently accessed data (models, tools)
7. **Optimistic Updates**: Update UI immediately, rollback on error

### Accessibility

1. **Keyboard Navigation**: Full keyboard support for all interactions
2. **Screen Readers**: Proper ARIA labels and descriptions
3. **Focus Management**: Logical focus order and visual indicators
4. **Color Contrast**: Meet WCAG 2.1 AA standards
5. **Alternative Text**: Descriptive alt text for all images
6. **Error Announcements**: Screen reader announcements for errors

### Security Best Practices

1. **Token Storage**: Use secure HTTP-only cookies or encrypted localStorage
2. **CSRF Protection**: Include CSRF tokens in state-changing requests
3. **Input Validation**: Validate all user inputs client-side and server-side
4. **Content Security Policy**: Implement strict CSP headers
5. **XSS Prevention**: Sanitize all user-generated content
6. **Sensitive Data**: Never log tokens or sensitive information

---

This API contract provides the complete specification for building a robust frontend that integrates seamlessly with the PrivateGPT backend. All endpoints, data models, and integration patterns are production-ready and designed for scalability.