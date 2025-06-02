"""
PrivateGPT Database Service
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .routers import documents, search, chat
from .services.weaviate_client import WeaviateService
from .services.embedding import EmbeddingService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting Database Service...")
    
    # Initialize Weaviate connection
    try:
        weaviate_service = WeaviateService()
        await weaviate_service.initialize()
        app.state.weaviate = weaviate_service
        logger.info("✅ Connected to Weaviate")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Weaviate: {e}")
        # Continue without Weaviate for now - services will handle gracefully
    
    # Initialize embedding service
    try:
        embedding_service = EmbeddingService()
        await embedding_service.initialize()
        app.state.embedding = embedding_service
        logger.info("✅ Embedding service initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize embedding service: {e}")
        # Continue - will be initialized on first use
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Database Service...")
    if hasattr(app.state, 'weaviate'):
        await app.state.weaviate.close()

# Create FastAPI app
app = FastAPI(
    title="PrivateGPT Database Service",
    description="Document processing and retrieval-augmented generation API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "PrivateGPT Database Service",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "documents": "/documents",
            "search": "/search", 
            "chat": "/chat",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "service": "database-service",
        "status": "healthy",
        "components": {},
        "version": "1.0.0"
    }
    
    # Check Weaviate connection
    if hasattr(app.state, 'weaviate'):
        try:
            # Simple check - could be enhanced with actual health ping
            health_status["components"]["weaviate"] = "connected"
        except Exception:
            health_status["components"]["weaviate"] = "disconnected"
            health_status["status"] = "degraded"
    else:
        health_status["components"]["weaviate"] = "not_configured"
        health_status["status"] = "degraded"
    
    # Check embedding service
    if hasattr(app.state, 'embedding'):
        try:
            health_status["components"]["embedding"] = "loaded"
        except Exception:
            health_status["components"]["embedding"] = "error"
    else:
        health_status["components"]["embedding"] = "not_loaded"
    
    return health_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 