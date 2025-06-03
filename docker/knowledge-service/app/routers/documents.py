"""
Document Management API Router
Upload, process, and manage legal documents
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from typing import Optional
import logging
import json
import base64
from datetime import datetime

from ..models.schemas import (
    DocumentResponse, DocumentListResponse, 
    DocumentUploadRequest
)
from ..services.weaviate_client import WeaviateService
from ..tasks.document_tasks import process_document_async, ProgressTracker

logger = logging.getLogger(__name__)
router = APIRouter()

def get_weaviate_service(request: Request) -> WeaviateService:
    """Get Weaviate service from app state"""
    if hasattr(request.app.state, 'weaviate'):
        return request.app.state.weaviate
    raise HTTPException(status_code=503, detail="Vector database unavailable")

# ================================
# DOCUMENT UPLOAD ENDPOINTS
# ================================

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(default="{}"),
):
    """
    Upload document for async processing with real-time progress tracking
    Returns task ID immediately for progress monitoring
    """
    try:
        # Basic validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename required")
        
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Parse metadata JSON
        try:
            doc_metadata = json.loads(metadata) if metadata != "{}" else {}
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
        
        # Encode file content for Celery task
        file_content_b64 = base64.b64encode(file_content).decode('utf-8')
        
        # Start async processing task
        task = process_document_async.delay(
            file_content_b64=file_content_b64,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename,
            metadata=doc_metadata
        )
        
        logger.info(f"Started async processing for {file.filename}, task_id: {task.id}")
        
        return {
            "task_id": task.id,
            "status": "ACCEPTED",
            "message": "Document upload accepted for processing",
            "filename": file.filename,
            "size": len(file_content),
            "progress_url": f"/documents/progress/{task.id}",
            "result_url": f"/documents/task-result/{task.id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Upload text content directly for async processing
@router.post("/upload-text")
async def upload_text_content(
    request: DocumentUploadRequest,
):
    try:
        if not request.content.strip():
            raise HTTPException(status_code=400, detail="Empty content")
        
        logger.info(f"Starting async text upload: {request.filename}")
        
        # Convert to bytes and encode for Celery task
        file_content = request.content.encode('utf-8')
        file_content_b64 = base64.b64encode(file_content).decode('utf-8')
        
        # Start async processing task
        task = process_document_async.delay(
            file_content_b64=file_content_b64,
            content_type=request.content_type,
            filename=request.filename,
            metadata=request.metadata
        )
        
        logger.info(f"Started async text processing for {request.filename}, task_id: {task.id}")
        
        return {
            "task_id": task.id,
            "status": "ACCEPTED",
            "message": "Text content accepted for processing",
            "filename": request.filename,
            "size": len(file_content),
            "progress_url": f"/documents/progress/{task.id}",
            "result_url": f"/documents/task-result/{task.id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

# ================================
# PROGRESS TRACKING ENDPOINTS
# ================================

@router.get("/progress/{task_id}")
async def get_upload_progress(task_id: str):
    """
    Get real-time progress for document processing task
    """
    try:
        # Get progress from Redis
        progress_data = ProgressTracker.get_progress(task_id)
        
        # Add task ID to response
        progress_data["task_id"] = task_id
        
        return progress_data
        
    except Exception as e:
        logger.error(f"Failed to get progress for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get progress")

@router.get("/task-result/{task_id}", response_model=DocumentResponse)
async def get_task_result(task_id: str):
    """
    Get final document result once async processing is complete
    """
    try:
        from ..celery_app import celery_app
        
        # Get task result from Celery
        task = celery_app.AsyncResult(task_id)
        
        if task.state == "PENDING":
            raise HTTPException(status_code=202, detail="Task is still processing")
        elif task.state == "SUCCESS":
            # Convert Celery result to DocumentResponse format
            result = task.result
            return DocumentResponse(
                id=result["document_id"],
                filename=result["filename"],
                content_type=result["content_type"],
                size=result["size"],
                chunk_count=result["chunk_count"],
                created_at=datetime.fromisoformat(result["created_at"]),
                metadata=result["metadata"]
            )
        elif task.state == "FAILURE":
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(task.info)}")
        else:
            raise HTTPException(status_code=202, detail=f"Task status: {task.state}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task result for {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task result")

# ================================
# DOCUMENT MANAGEMENT ENDPOINTS
# ================================

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """Get paginated list of all uploaded documents"""
    try:
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=400, detail="Page size: 1-100")
        
        result = await weaviate.list_documents(page=page, page_size=page_size)
        
        # Convert to API response format
        documents = []
        for doc_info in result["documents"]:
            doc_response = DocumentResponse(
                id=doc_info["id"],
                filename=doc_info["filename"],
                content_type=doc_info["content_type"],
                size=0,  # Size not stored in vector DB
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
        
        logger.info(f"Listed {len(documents)} documents (page {page})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """Get information about a specific document"""
    try:
        doc_info = await weaviate.get_document_info(document_id)
        
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        response = DocumentResponse(
            id=doc_info["id"],
            filename=doc_info["filename"],
            content_type=doc_info["content_type"],
            size=0,  # Size not available in vector DB
            chunk_count=0,  # Would need separate query
            created_at=datetime.fromisoformat(doc_info["created_at"].replace("Z", "+00:00")),
            metadata=doc_info["metadata"]
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """Delete a document and all its chunks"""
    try:
        # Verify document exists
        doc_info = await weaviate.get_document_info(document_id)
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete all chunks for this document
        deleted_count = await weaviate.delete_document(document_id)
        
        logger.info(f"Deleted document {document_id} ({deleted_count} chunks)")
        
        return {
            "message": "Document deleted successfully",
            "document_id": document_id,
            "chunks_deleted": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """Get all chunks for a specific document"""
    try:
        # Use dummy embedding with document filter to get all chunks
        dummy_embedding = [0.0] * 384  # BGE-small embedding dimension
        
        results = await weaviate.search_similar(
            query_embedding=dummy_embedding,
            limit=1000,  # Get all chunks
            threshold=0.0,  # Accept all results
            filters={"document_id": document_id}
        )
        
        if not results:
            raise HTTPException(status_code=404, detail="Document not found or no chunks")
        
        return {
            "document_id": document_id,
            "chunks": results,
            "total_chunks": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chunks for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 