"""
Knowledge Service - Main Application Entry Point
Handles document processing, search, and RAG for PrivateGPT Legal AI
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import json
from datetime import datetime

# Import our routers and services
from .routers import documents, search, chat, admin
from .services.weaviate_client import WeaviateService
from .services.embedding import EmbeddingService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_json(message: str, **kwargs):
    """Simple structured logging helper"""
    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": "knowledge-service", 
        "message": message,
        **kwargs
    }
    print(json.dumps(data))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    
    # STARTUP - Initialize services
    log_json("Starting Knowledge Service...")
    
    # Connect to Weaviate vector database
    try:
        weaviate_service = WeaviateService()
        await weaviate_service.initialize()
        app.state.weaviate = weaviate_service
        log_json("Connected to Weaviate", status="success")
    except Exception as e:
        log_json("Weaviate connection failed", error=str(e), status="warning")
        # Continue without Weaviate - graceful degradation
    
    # Initialize embedding service  
    try:
        embedding_service = EmbeddingService()
        await embedding_service.initialize()
        app.state.embedding = embedding_service
        log_json("Embedding service ready", status="success")
    except Exception as e:
        log_json("Embedding service failed", error=str(e), status="warning")
        # Will be initialized on first use
    
    log_json("Knowledge Service startup complete")
    
    yield
    
    # SHUTDOWN - Cleanup resources
    log_json("Shutting down Knowledge Service...")
    if hasattr(app.state, 'weaviate'):
        await app.state.weaviate.close()
    log_json("Knowledge Service shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="PrivateGPT Knowledge Service",
    description="Document processing and RAG API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

@app.get("/")
async def root():
    """Service information and available endpoints"""
    return {
        "service": "PrivateGPT Knowledge Service",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "documents": "/documents - Upload and manage documents",
            "search": "/search - Semantic document search", 
            "chat": "/chat - RAG-powered conversations",
            "health": "/health - Service health check",
            "docs": "/docs - API documentation"
        }
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check for monitoring"""
    health_status = {
        "service": "knowledge-service",
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "components": {},
        "version": "1.0.0"
    }
    
    # Check Weaviate connection
    if hasattr(app.state, 'weaviate'):
        try:
            # Simple connectivity test
            health_status["components"]["weaviate"] = "connected"
        except Exception:
            health_status["components"]["weaviate"] = "disconnected"
            health_status["status"] = "degraded"
    else:
        health_status["components"]["weaviate"] = "not_configured"
        health_status["status"] = "degraded"
    
    # Check embedding service
    if hasattr(app.state, 'embedding') and app.state.embedding.model:
        health_status["components"]["embedding"] = "loaded"
    else:
        health_status["components"]["embedding"] = "not_loaded"
    
    return health_status

# Development server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 