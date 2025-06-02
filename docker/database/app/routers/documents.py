"""
Document management router
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional, List
import logging
import time
from datetime import datetime

from ..models.schemas import (
    DocumentResponse, DocumentListResponse, ErrorResponse,
    DocumentUploadRequest
)
from ..services.weaviate_client import WeaviateService
from ..services.embedding import EmbeddingService
from ..services.chunking import ChunkingService

logger = logging.getLogger(__name__)

router = APIRouter()

# Service instances (will be initialized on startup)
chunking_service = ChunkingService()
embedding_service = EmbeddingService()


async def get_weaviate_service() -> WeaviateService:
    """Dependency to get Weaviate service from app state"""
    from fastapi import Request
    request = Request.scope
    if hasattr(request.app.state, 'weaviate'):
        return request.app.state.weaviate
    raise HTTPException(status_code=503, detail="Weaviate service not available")


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(default="{}"),
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    Upload and process a document
    
    Supports PDF, DOCX, and text files.
    Returns document information after processing and storing.
    """
    start_time = time.time()
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Read file content
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        logger.info(f"📁 Processing upload: {file.filename} ({len(file_content)} bytes)")
        
        # Parse metadata
        import json
        try:
            doc_metadata = json.loads(metadata) if metadata != "{}" else {}
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
        
        # Process document (extract text and chunk)
        doc_result = await chunking_service.process_document(
            file_content=file_content,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename,
            metadata=doc_metadata
        )
        
        # Initialize embedding service if needed
        if not embedding_service.model:
            await embedding_service.initialize()
        
        # Generate embeddings for all chunks
        chunk_texts = [chunk["content"] for chunk in doc_result["chunks"]]
        embeddings = await embedding_service.embed_texts(chunk_texts)
        
        # Store in Weaviate
        chunk_ids = await weaviate.store_document_chunks(
            document_id=doc_result["document_id"],
            chunks=doc_result["chunks"],
            embeddings=embeddings
        )
        
        # Prepare response
        response = DocumentResponse(
            id=doc_result["document_id"],
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            size=len(file_content),
            chunk_count=len(doc_result["chunks"]),
            created_at=datetime.utcnow(),
            metadata=doc_result["metadata"]
        )
        
        processing_time = (time.time() - start_time) * 1000
        logger.info(f"✅ Document processed in {processing_time:.1f}ms: {file.filename}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/upload-text", response_model=DocumentResponse)
async def upload_text_content(
    request: DocumentUploadRequest,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    Upload text content directly (without file)
    
    Useful for pasting text or programmatic uploads.
    """
    start_time = time.time()
    
    try:
        if not request.content.strip():
            raise HTTPException(status_code=400, detail="Empty content")
        
        logger.info(f"📝 Processing text upload: {request.filename}")
        
        # Convert to bytes for consistency with file processing
        file_content = request.content.encode('utf-8')
        
        # Process document
        doc_result = await chunking_service.process_document(
            file_content=file_content,
            content_type=request.content_type,
            filename=request.filename,
            metadata=request.metadata
        )
        
        # Initialize embedding service if needed
        if not embedding_service.model:
            await embedding_service.initialize()
        
        # Generate embeddings
        chunk_texts = [chunk["content"] for chunk in doc_result["chunks"]]
        embeddings = await embedding_service.embed_texts(chunk_texts)
        
        # Store in Weaviate
        chunk_ids = await weaviate.store_document_chunks(
            document_id=doc_result["document_id"],
            chunks=doc_result["chunks"],
            embeddings=embeddings
        )
        
        # Prepare response
        response = DocumentResponse(
            id=doc_result["document_id"],
            filename=request.filename,
            content_type=request.content_type,
            size=len(file_content),
            chunk_count=len(doc_result["chunks"]),
            created_at=datetime.utcnow(),
            metadata=doc_result["metadata"]
        )
        
        processing_time = (time.time() - start_time) * 1000
        logger.info(f"✅ Text content processed in {processing_time:.1f}ms")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Text upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    List all uploaded documents with pagination
    """
    try:
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=400, detail="Page size must be between 1 and 100")
        
        result = await weaviate.list_documents(page=page, page_size=page_size)
        
        # Convert to response format
        documents = []
        for doc_info in result["documents"]:
            doc_response = DocumentResponse(
                id=doc_info["id"],
                filename=doc_info["filename"],
                content_type=doc_info["content_type"],
                size=0,  # Size not available in this context
                chunk_count=doc_info["chunk_count"],
                created_at=datetime.fromisoformat(doc_info["created_at"].replace("Z", "+00:00")),
                metadata=doc_info["metadata"]
            )
            documents.append(doc_response)
        
        response = DocumentListResponse(
            documents=documents,
            total=result["total"],
            page=page,
            page_size=page_size
        )
        
        logger.info(f"📄 Listed {len(documents)} documents (page {page})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    Get information about a specific document
    """
    try:
        doc_info = await weaviate.get_document_info(document_id)
        
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        response = DocumentResponse(
            id=doc_info["id"],
            filename=doc_info["filename"],
            content_type=doc_info["content_type"],
            size=0,  # Size not available in this context
            chunk_count=0,  # Would need separate query
            created_at=datetime.fromisoformat(doc_info["created_at"].replace("Z", "+00:00")),
            metadata=doc_info["metadata"]
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    Delete a document and all its chunks
    """
    try:
        # Check if document exists
        doc_info = await weaviate.get_document_info(document_id)
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete from Weaviate
        deleted_count = await weaviate.delete_document(document_id)
        
        logger.info(f"🗑️ Deleted document {document_id} ({deleted_count} chunks)")
        
        return {
            "message": f"Document deleted successfully",
            "document_id": document_id,
            "chunks_deleted": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    Get all chunks for a specific document
    """
    try:
        # Search for chunks of this document
        # Use a dummy embedding (all zeros) with document filter
        dummy_embedding = [0.0] * 384  # BGE-small embedding dimension
        
        results = await weaviate.search_similar(
            query_embedding=dummy_embedding,
            limit=1000,  # Large limit to get all chunks
            threshold=0.0,  # Accept all
            filters={"document_id": document_id}
        )
        
        if not results:
            raise HTTPException(status_code=404, detail="Document not found or has no chunks")
        
        return {
            "document_id": document_id,
            "chunks": results,
            "total_chunks": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get chunks for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chunks: {str(e)}") 