# 🏛️ Legal AI Weaviate FastAPI Service

A production-ready FastAPI service for legal document management and semantic search using Weaviate vector database with comprehensive logging and compliance features.

## 🚀 Features

- **FastAPI REST API** - Modern, fast, and well-documented API
- **Weaviate Integration** - Vector database with semantic search capabilities
- **Comprehensive Logging** - Request/response logging, audit trails, and error tracking
- **Legal Compliance** - Client matter segregation, audit trails, and data governance
- **Health Monitoring** - Health checks and service statistics
- **Type Safety** - Full Pydantic models with validation
- **Auto Documentation** - Interactive API docs with Swagger/OpenAPI

## 📋 Requirements

- Python 3.8+
- Weaviate database instance
- Dependencies listed in `requirements.txt`

## 🛠️ Installation

1. **Clone/Download the service files:**
   ```bash
   # Main service file: weaviate_service.py
   # Client example: client_example.py
   # Requirements: requirements.txt
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp config.env.example .env
   # Edit .env with your Weaviate configuration
   ```

4. **Create logs directory:**
   ```bash
   mkdir logs
   ```

## ⚙️ Configuration

Set your Weaviate connection details:

```bash
# .env file
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=your-api-key-here  # Optional, leave empty if no auth
```

## 🏃‍♂️ Running the Service

### Development Mode
```bash
python weaviate_service.py
```

### Production Mode with uvicorn
```bash
uvicorn weaviate_service:app --host 0.0.0.0 --port 8002 --workers 4
```

### Docker (Optional)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8002

CMD ["uvicorn", "weaviate_service:app", "--host", "0.0.0.0", "--port", "8002"]
```

## 📖 API Documentation

Once running, access interactive documentation at:
- **Swagger UI:** http://localhost:8002/docs
- **ReDoc:** http://localhost:8002/redoc

## 🔌 API Endpoints

### Document Management

#### Add Document
```http
POST /documents/add
Content-Type: application/json

{
  "content": "Full document text content...",
  "filename": "contract.pdf",
  "client_matter": "ClientA_Matter_2024",
  "doc_type": "contract",
  "uploaded_by": "attorney@firm.com"
}
```

#### Search Documents
```http
POST /documents/search
Content-Type: application/json

{
  "query": "employment contract terms",
  "limit": 5,
  "client_matter": "ClientA_Matter_2024",  // Optional filter
  "doc_type": "contract",                   // Optional filter
  "min_score": 0.7                         // Optional minimum relevance
}
```

### System Monitoring

#### Health Check
```http
GET /health
```

#### Statistics
```http
GET /documents/stats
```

## 🐍 Client Usage Example

```python
from client_example import LegalAIClient

# Initialize client
client = LegalAIClient("http://localhost:8002")

# Add a document
result = client.add_document(
    content="This is a legal contract...",
    filename="sample_contract.pdf",
    client_matter="Client_A_Matter_001",
    doc_type="contract",
    uploaded_by="attorney@firm.com"
)

# Search documents
results = client.search_documents(
    query="contract terms and conditions",
    limit=5,
    client_matter="Client_A_Matter_001"
)

print(f"Found {results['count']} documents")
for doc in results['results']:
    print(f"- {doc['source']} (Score: {doc['score']:.3f})")
```

## 🔍 Running the Demo

Test the service with sample legal documents:

```bash
# Make sure the service is running first
python weaviate_service.py

# In another terminal, run the demo
python client_example.py
```

The demo will:
1. Check service health
2. Add 3 sample legal documents
3. Run 4 different search examples
4. Display database statistics

## 📊 Logging and Monitoring

### Log Files
- **Service logs:** `logs/weaviate_service.log`
- **Request/response logging** with timing information
- **Error tracking** with full stack traces
- **Audit trail** for document operations

### Log Format
```
2024-01-15 10:30:45,123 - legal_ai_weaviate - INFO - DOCUMENT_ADD_START - ID: abc123... - File: contract.pdf - Matter: ClientA_Matter_2024
2024-01-15 10:30:45,156 - legal_ai_weaviate - INFO - DOCUMENT_ADD_SUCCESS - ID: abc123... - Content length: 2048 chars
```

### Monitored Events
- Document additions with metadata
- Search queries with performance metrics
- Health check results
- Error conditions and exceptions
- Request/response cycles with timing

## 🛡️ Security Features

### Data Segregation
- **Client Matter Filtering:** Documents are isolated by client matter
- **Role-based Access:** Ready for authentication integration
- **Audit Logging:** All operations are logged for compliance

### Input Validation
- **Pydantic Models:** Type checking and validation
- **Size Limits:** Configurable document size limits
- **Schema Validation:** Enforced data structure

## 📈 Performance Considerations

### Optimization
- **Connection Pooling:** Reused Weaviate connections
- **Async Operations:** Non-blocking request handling
- **Caching:** Service-level caching for repeated operations

### Scaling
- **Horizontal Scaling:** Multiple worker processes
- **Load Balancing:** Ready for reverse proxy deployment
- **Health Checks:** Built-in monitoring for orchestration

## 🔧 Integration Examples

### With Existing Systems

#### Add Authentication Middleware
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.middleware("http")
async def authenticate_request(request: Request, call_next):
    # Add your authentication logic here
    response = await call_next(request)
    return response
```

#### Connect to Your Weaviate Instance
```python
# Update connection in weaviate_service.py
WEAVIATE_URL = "https://your-weaviate-cluster.weaviate.network"
WEAVIATE_API_KEY = "your-production-api-key"
```

### With Document Processing
```python
import PyPDF2
from weaviate_service import DocumentInput

def process_and_add_pdf(pdf_file, client_matter):
    # Extract text
    text = extract_pdf_text(pdf_file)
    
    # Add to Weaviate via API
    doc_input = DocumentInput(
        content=text,
        filename=pdf_file.name,
        client_matter=client_matter,
        doc_type="contract",
        uploaded_by="system"
    )
    
    return weaviate_service.add_document(doc_input)
```

## 🐛 Troubleshooting

### Common Issues

#### Connection Errors
```bash
# Check Weaviate is running
curl http://localhost:8080/v1/schema

# Check service logs
tail -f logs/weaviate_service.log
```

#### Schema Issues
```bash
# Reset schema (WARNING: deletes all data)
curl -X DELETE http://localhost:8080/v1/schema/LegalDocument
```

#### Performance Issues
- Check Weaviate resource usage
- Monitor log file for slow queries
- Consider adding indexes for frequently filtered fields

### Debug Mode
```python
# Enable debug logging
import logging
logging.getLogger("legal_ai_weaviate").setLevel(logging.DEBUG)
```

## 📝 Legal Compliance

### Audit Trail
- Every document operation is logged
- Timestamps for all activities
- User attribution for changes
- Search query logging for discovery

### Data Governance
- Client matter segregation
- Configurable data retention
- Export capabilities for compliance
- Deletion and archival support

## 🤝 Contributing

1. Follow PEP 8 style guidelines
2. Add type hints for all functions
3. Include comprehensive docstrings
4. Add appropriate logging statements
5. Update tests for new features

## 📄 License

This service is designed for legal professionals and should be deployed in compliance with attorney-client privilege and data protection regulations.

---

**⚖️ Built for Legal Professionals** - Ensuring data sovereignty, compliance, and security in legal AI applications. 