"""
Legal AI Weaviate FastAPI Service
Provides REST API endpoints for document management with comprehensive logging
"""

import os
import uuid
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import weaviate
from weaviate.exceptions import WeaviateException

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/weaviate_service.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("legal_ai_weaviate")

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# FastAPI app
app = FastAPI(
    title="Legal AI Weaviate Service",
    description="Document management and semantic search API for legal professionals",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(
        f"REQUEST_START - {request.method} {request.url.path} - "
        f"Client: {client_ip} - User-Agent: {request.headers.get('user-agent', 'unknown')}"
    )
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"REQUEST_END - {request.method} {request.url.path} - "
        f"Status: {response.status_code} - Duration: {process_time:.3f}s"
    )
    
    return response

# Pydantic models
class DocumentInput(BaseModel):
    content: str = Field(..., description="Full document text content")
    filename: str = Field(..., description="Original filename")
    client_matter: str = Field(..., description="Client matter identifier")
    doc_type: str = Field(..., description="Document type (contract, case_law, filing, etc.)")
    uploaded_by: str = Field(default="system", description="User who uploaded the document")

class SearchQuery(BaseModel):
    query: str = Field(..., description="Search query text")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of results")
    client_matter: Optional[str] = Field(default=None, description="Filter by client matter")
    doc_type: Optional[str] = Field(default=None, description="Filter by document type")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum relevance score")

class DocumentResponse(BaseModel):
    document_id: str
    status: str
    message: str
    timestamp: str

class SearchResult(BaseModel):
    content: str
    source: str
    doc_type: str
    client_matter: str
    document_id: str
    score: float
    created_at: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    count: int
    query: str
    search_time_ms: float

class StatsResponse(BaseModel):
    total_documents: int
    document_types: Dict[str, int]
    client_matters: Dict[str, int]
    status: str
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    weaviate_connected: bool
    schema_exists: bool
    timestamp: str
    version: str

# Weaviate service class
class WeaviateService:
    """Enhanced Weaviate service with comprehensive logging"""
    
    def __init__(self, weaviate_url: str, api_key: Optional[str] = None):
        self.weaviate_url = weaviate_url
        self.api_key = api_key
        
        logger.info(f"Initializing Weaviate service - URL: {weaviate_url}")
        
        try:
            if api_key:
                self.client = weaviate.Client(
                    url=weaviate_url,
                    auth_client_secret=weaviate.AuthApiKey(api_key=api_key),
                    additional_headers={"X-OpenAI-Api-Key": "placeholder"}
                )
                logger.info("Weaviate client initialized with API key authentication")
            else:
                self.client = weaviate.Client(
                    url=weaviate_url,
                    additional_headers={"X-OpenAI-Api-Key": "placeholder"}
                )
                logger.info("Weaviate client initialized without authentication")
            
            self._ensure_schema()
            logger.info("Weaviate service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate service: {str(e)}")
            raise
    
    def _ensure_schema(self):
        """Ensure the LegalDocument schema exists"""
        logger.info("Checking/creating Weaviate schema")
        
        schema = {
            "class": "LegalDocument",
            "description": "Legal documents for AI analysis with audit trail",
            "vectorizer": "text2vec-transformers",
            "moduleConfig": {
                "text2vec-transformers": {
                    "poolingStrategy": "masked_mean",
                    "vectorizeClassName": False
                }
            },
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Full document text content"
                },
                {
                    "name": "source",
                    "dataType": ["string"],
                    "description": "Source document filename"
                },
                {
                    "name": "docType",
                    "dataType": ["string"],
                    "description": "Document type (contract, case_law, filing, memo, etc.)"
                },
                {
                    "name": "clientMatter",
                    "dataType": ["string"],
                    "description": "Client matter code for data segregation"
                },
                {
                    "name": "documentId",
                    "dataType": ["string"],
                    "description": "Unique document identifier"
                },
                {
                    "name": "createdAt",
                    "dataType": ["date"],
                    "description": "Document ingestion timestamp"
                },
                {
                    "name": "uploadedBy",
                    "dataType": ["string"],
                    "description": "User who uploaded the document"
                },
                {
                    "name": "fileSize",
                    "dataType": ["int"],
                    "description": "Original file size in bytes"
                },
                {
                    "name": "contentLength",
                    "dataType": ["int"],
                    "description": "Extracted content length"
                }
            ]
        }
        
        try:
            existing_schema = self.client.schema.get()
            existing_classes = [cls["class"] for cls in existing_schema.get("classes", [])]
            
            if "LegalDocument" not in existing_classes:
                self.client.schema.create_class(schema)
                logger.info("Created LegalDocument schema in Weaviate")
            else:
                logger.info("LegalDocument schema already exists")
                
        except Exception as e:
            logger.error(f"Error managing Weaviate schema: {str(e)}")
            raise
    
    def add_document(self, doc_input: DocumentInput) -> str:
        """Add document to Weaviate"""
        document_id = str(uuid.uuid4())
        
        logger.info(
            f"DOCUMENT_ADD_START - ID: {document_id} - "
            f"File: {doc_input.filename} - Matter: {doc_input.client_matter} - "
            f"Type: {doc_input.doc_type} - User: {doc_input.uploaded_by}"
        )
        
        try:
            document_obj = {
                "content": doc_input.content,
                "source": doc_input.filename,
                "docType": doc_input.doc_type,
                "clientMatter": doc_input.client_matter,
                "documentId": document_id,
                "uploadedBy": doc_input.uploaded_by,
                "createdAt": datetime.now().isoformat(),
                "fileSize": len(doc_input.content.encode('utf-8')),
                "contentLength": len(doc_input.content)
            }
            
            self.client.data_object.create(
                data_object=document_obj,
                class_name="LegalDocument"
            )
            
            logger.info(
                f"DOCUMENT_ADD_SUCCESS - ID: {document_id} - "
                f"Content length: {len(doc_input.content)} chars"
            )
            
            return document_id
            
        except Exception as e:
            logger.error(
                f"DOCUMENT_ADD_ERROR - ID: {document_id} - "
                f"File: {doc_input.filename} - Error: {str(e)}"
            )
            raise
    
    def search_documents(self, search_query: SearchQuery) -> Dict[str, Any]:
        """Search documents with detailed logging"""
        start_time = time.time()
        
        logger.info(
            f"SEARCH_START - Query: '{search_query.query}' - "
            f"Limit: {search_query.limit} - Matter: {search_query.client_matter} - "
            f"Type: {search_query.doc_type}"
        )
        
        try:
            # Build the query
            result_query = (
                self.client.query
                .get("LegalDocument", [
                    "content", "source", "docType", "clientMatter", 
                    "documentId", "createdAt", "uploadedBy"
                ])
                .with_near_text({"concepts": [search_query.query]})
                .with_limit(search_query.limit)
                .with_additional(["certainty"])
            )
            
            # Apply filters
            where_conditions = []
            
            if search_query.client_matter:
                where_conditions.append({
                    "path": ["clientMatter"],
                    "operator": "Equal",
                    "valueString": search_query.client_matter
                })
            
            if search_query.doc_type:
                where_conditions.append({
                    "path": ["docType"],
                    "operator": "Equal",
                    "valueString": search_query.doc_type
                })
            
            if where_conditions:
                if len(where_conditions) == 1:
                    result_query = result_query.with_where(where_conditions[0])
                else:
                    result_query = result_query.with_where({
                        "operator": "And",
                        "operands": where_conditions
                    })
            
            # Execute query
            response = result_query.do()
            documents = response.get("data", {}).get("Get", {}).get("LegalDocument", [])
            
            # Filter by minimum score
            filtered_docs = [
                doc for doc in documents 
                if doc["_additional"]["certainty"] >= search_query.min_score
            ]
            
            search_time = (time.time() - start_time) * 1000  # Convert to ms
            
            results = [
                SearchResult(
                    content=doc["content"],
                    source=doc["source"],
                    doc_type=doc["docType"],
                    client_matter=doc["clientMatter"],
                    document_id=doc["documentId"],
                    score=doc["_additional"]["certainty"],
                    created_at=doc.get("createdAt", "")
                )
                for doc in filtered_docs
            ]
            
            logger.info(
                f"SEARCH_SUCCESS - Query: '{search_query.query}' - "
                f"Results: {len(results)} - Time: {search_time:.2f}ms"
            )
            
            return {
                "results": results,
                "count": len(results),
                "query": search_query.query,
                "search_time_ms": search_time
            }
            
        except Exception as e:
            search_time = (time.time() - start_time) * 1000
            logger.error(
                f"SEARCH_ERROR - Query: '{search_query.query}' - "
                f"Time: {search_time:.2f}ms - Error: {str(e)}"
            )
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics with logging"""
        logger.info("STATS_REQUEST - Fetching database statistics")
        
        try:
            # Get total document count
            result = (
                self.client.query
                .aggregate("LegalDocument")
                .with_meta_count()
                .do()
            )
            
            total_docs = result["data"]["Aggregate"]["LegalDocument"][0]["meta"]["count"]
            
            # Get document types distribution
            doc_types_result = (
                self.client.query
                .aggregate("LegalDocument")
                .with_group_by_filter(["docType"])
                .with_meta_count()
                .do()
            )
            
            doc_types = {}
            for group in doc_types_result["data"]["Aggregate"]["LegalDocument"]:
                doc_type = group["groupedBy"]["value"]
                count = group["meta"]["count"]
                doc_types[doc_type] = count
            
            # Get client matters distribution
            matters_result = (
                self.client.query
                .aggregate("LegalDocument")
                .with_group_by_filter(["clientMatter"])
                .with_meta_count()
                .do()
            )
            
            client_matters = {}
            for group in matters_result["data"]["Aggregate"]["LegalDocument"]:
                matter = group["groupedBy"]["value"]
                count = group["meta"]["count"]
                client_matters[matter] = count
            
            stats = {
                "total_documents": total_docs,
                "document_types": doc_types,
                "client_matters": client_matters,
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"STATS_SUCCESS - Total docs: {total_docs}")
            return stats
            
        except Exception as e:
            logger.error(f"STATS_ERROR - Error: {str(e)}")
            return {
                "total_documents": 0,
                "document_types": {},
                "client_matters": {},
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check with logging"""
        logger.info("HEALTH_CHECK - Starting health verification")
        
        weaviate_connected = False
        schema_exists = False
        
        try:
            # Test connection
            self.client.schema.get()
            weaviate_connected = True
            logger.info("HEALTH_CHECK - Weaviate connection: OK")
            
            # Check schema
            schema = self.client.schema.get()
            existing_classes = [cls["class"] for cls in schema.get("classes", [])]
            schema_exists = "LegalDocument" in existing_classes
            logger.info(f"HEALTH_CHECK - Schema exists: {schema_exists}")
            
        except Exception as e:
            logger.error(f"HEALTH_CHECK - Error: {str(e)}")
        
        health_status = "healthy" if (weaviate_connected and schema_exists) else "unhealthy"
        
        return {
            "status": health_status,
            "weaviate_connected": weaviate_connected,
            "schema_exists": schema_exists,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }

# Initialize Weaviate service
def get_weaviate_service() -> WeaviateService:
    """Dependency to get Weaviate service instance"""
    weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    api_key = os.getenv("WEAVIATE_API_KEY")
    
    try:
        return WeaviateService(weaviate_url, api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Weaviate service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weaviate service unavailable"
        )

# API Endpoints
@app.post("/documents/add", response_model=DocumentResponse)
async def add_document(
    doc_input: DocumentInput,
    weaviate_service: WeaviateService = Depends(get_weaviate_service)
):
    """Add a legal document to the vector database"""
    try:
        document_id = weaviate_service.add_document(doc_input)
        
        return DocumentResponse(
            document_id=document_id,
            status="success",
            message="Document added successfully",
            timestamp=datetime.now().isoformat()
        )
        
    except WeaviateException as e:
        logger.error(f"Weaviate error adding document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error adding document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/documents/search", response_model=SearchResponse)
async def search_documents(
    search_query: SearchQuery,
    weaviate_service: WeaviateService = Depends(get_weaviate_service)
):
    """Search legal documents using semantic search"""
    try:
        results = weaviate_service.search_documents(search_query)
        return SearchResponse(**results)
        
    except WeaviateException as e:
        logger.error(f"Weaviate error during search: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during search: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/documents/stats", response_model=StatsResponse)
async def get_statistics(
    weaviate_service: WeaviateService = Depends(get_weaviate_service)
):
    """Get database statistics and metrics"""
    try:
        stats = weaviate_service.get_stats()
        return StatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error fetching statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching statistics"
        )

@app.get("/health", response_model=HealthResponse)
async def health_check(
    weaviate_service: WeaviateService = Depends(get_weaviate_service)
):
    """Health check endpoint for monitoring"""
    try:
        health = weaviate_service.health_check()
        
        if health["status"] == "unhealthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unhealthy"
            )
        
        return HealthResponse(**health)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Legal AI Weaviate Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    logger.warning(f"404 - Path not found: {request.url.path}")
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"500 - Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    logger.info("Starting Legal AI Weaviate Service")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info",
        access_log=True
    ) 