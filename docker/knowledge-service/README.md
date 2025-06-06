# Knowledge Service

The Knowledge Service is a FastAPI-based microservice that handles document processing, storage, and retrieval-augmented generation (RAG) for the PrivateGPT system.

## Features

- **Document Processing**: Upload and process various document types (PDF, TXT, DOCX)
- **Vector Storage**: Store and retrieve document embeddings using Weaviate
- **Semantic Search**: Find relevant documents based on semantic similarity
- **RAG Chat**: Generate responses using retrieved context and LLM integration
- **Health Monitoring**: Built-in health checks and monitoring endpoints

## Quick Start

### Docker (Recommended)

```bash
# Build the image
docker build -t knowledge-service .

# Run the container
docker-compose up knowledge-service
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   N8N Workflows  │    │   External      │
│   Frontend      │────│   Automation     │────│   Clients       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────────────┐
                    │   Database Service      │
                    │   (FastAPI)             │
                    └─────────────────────────┘
                                 │
                    ┌─────────────────────────┐
                    │   Weaviate Vector DB    │
                    └─────────────────────────┘
```

## API Endpoints

### Documents
- `POST /documents/upload` - Upload file for processing
- `POST /documents/upload-text` - Upload text content directly
- `GET /documents/` - List all documents (paginated)
- `GET /documents/{id}` - Get document details
- `DELETE /documents/{id}` - Delete document and chunks
- `GET /documents/{id}/chunks` - Get all chunks for document

### Search
- `POST /search/` - Vector similarity search
- `GET /search/similar/{document_id}` - Find similar documents
- `POST /search/semantic` - Advanced semantic search
- `GET /search/suggestions` - Get search suggestions

### Chat
- `POST /chat/` - RAG-powered chat with documents
- `POST /chat/stream` - Streaming chat responses
- `POST /chat/explain` - Explain answer sources
- `GET /chat/models` - List available LLM models

### Health
- `GET /health` - Service health check
- `GET /` - Service information

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEAVIATE_URL` | `http://weaviate-db:8080` | Weaviate database URL |
| `OLLAMA_URL` | `http://ollama-service:11434` | Ollama LLM service URL |
| `OLLAMA_MODEL` | `llama3:8b` | LLM model to use |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model |
| `CHUNK_SIZE` | `1000` | Maximum characters per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |

## Usage Examples

### Upload a Document
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -F "file=@document.pdf" \
  -F "metadata={\"category\": \"legal\"}"
```

### Search Documents
```bash
curl -X POST "http://localhost:8000/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "contract terms and conditions",
    "limit": 5,
    "threshold": 0.7
  }'
```

### Chat with Documents
```bash
curl -X POST "http://localhost:8000/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What are the key terms in the uploaded contracts?"}
    ],
    "max_tokens": 1000,
    "include_sources": true
  }'
```

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Development
```bash
# Build the image
docker build -t knowledge-service .

# Run with docker-compose
docker-compose up knowledge-service
```

## Service Dependencies

- **Weaviate**: Vector database for document storage and search
- **Ollama**: LLM service for chat responses
- **BGE Embeddings**: Sentence transformer model for embeddings

## Monitoring

The service includes:
- Health check endpoints
- Structured logging
- Performance metrics
- Error handling with detailed responses

## API Documentation

When running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc` 