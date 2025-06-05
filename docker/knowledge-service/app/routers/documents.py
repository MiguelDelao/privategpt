"""
Document Management API Router
Upload, process, and manage legal documents
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from typing import Optional, List
import logging
import json
import base64
from datetime import datetime

from ..models.schemas import (
    DocumentResponse, DocumentListResponse, 
    DocumentUploadRequest, DocumentUploadAcceptedResponse, TaskProgressData
)
from ..services.weaviate_client import WeaviateService
from ..tasks.document_tasks import process_document_async, ProgressTracker
from ..dependencies import get_auth_context, AuthContext

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

@router.post("/upload", response_model=DocumentUploadAcceptedResponse)
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(default="{}"),
    client_id: Optional[str] = Form(None),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """
    Upload document for async processing with real-time progress tracking
    Returns task ID immediately for progress monitoring
    Optionally accepts client_id for associating the document with a specific client
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
        
        # Handle client_id authorization
        if client_id:
            # If a specific client_id is provided, verify the user has access to it
            has_access = await auth_context.auth_client.verify_access(
                auth_context.user_id, client_id, "upload_docs"
            )
            if not has_access:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: You do not have permission to upload documents for client {client_id}"
                )
        else:
            # If no client_id provided, default to "all" (requires no specific permission for now)
            client_id = "all"
        
        # Add client_id to the metadata
        doc_metadata['client_id'] = client_id
        
        # Encode file content for Celery task
        file_content_b64 = base64.b64encode(file_content).decode('utf-8')
        
        # Start async processing task
        task = process_document_async.delay(
            file_content_b64=file_content_b64,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename,
            metadata=doc_metadata
        )
        
        logger.info(f"Started async processing for {file.filename} (Client: {client_id or 'all'}), task_id: {task.id}")
        
        return DocumentUploadAcceptedResponse(
            message="Document upload accepted for processing.",
            task_id=task.id,
            filename=file.filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Upload text content directly for async processing
@router.post("/upload-text", response_model=DocumentUploadAcceptedResponse)
async def upload_text_content(
    filename: str = Form(...),
    content: str = Form(...),
    content_type: str = Form("text/plain"),
    metadata_json: Optional[str] = Form(default="{}"),
    client_id: Optional[str] = Form(None),
    auth_context: AuthContext = Depends(get_auth_context),
):
    try:
        if not content.strip():
            raise HTTPException(status_code=400, detail="Empty content")
        
        logger.info(f"Starting async text upload: {filename} (Client: {client_id or 'all'})")
        
        try:
            doc_metadata = json.loads(metadata_json) if metadata_json != "{}" else {}
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON in metadata_json field")
        
        # Handle client_id authorization
        if client_id:
            # If a specific client_id is provided, verify the user has access to it
            has_access = await auth_context.auth_client.verify_access(
                auth_context.user_id, client_id, "upload_docs"
            )
            if not has_access:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: You do not have permission to upload documents for client {client_id}"
                )
        else:
            # If no client_id provided, default to "all" (requires no specific permission for now)
            client_id = "all"
        
        # Add client_id to the metadata
        doc_metadata['client_id'] = client_id
        
        file_content_bytes = content.encode('utf-8')
        file_content_b64 = base64.b64encode(file_content_bytes).decode('utf-8')
        
        task = process_document_async.delay(
            file_content_b64=file_content_b64,
            content_type=content_type,
            filename=filename,
            metadata=doc_metadata
        )
        
        logger.info(f"Started async text processing for {filename}, task_id: {task.id}")
        
        return DocumentUploadAcceptedResponse(
            message="Text content accepted for processing.",
            task_id=task.id,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text upload failed for {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

# ================================
# PROGRESS TRACKING ENDPOINTS
# ================================

@router.get("/task_progress/{task_id}", response_model=TaskProgressData)
async def get_task_progress(task_id: str):
    """
    Get real-time progress for a specific document processing Celery task
    """
    try:
        progress_data = ProgressTracker.get_progress(task_id)
        
        # Handle old data format - fix result object if it has document_id instead of id
        if "result" in progress_data and isinstance(progress_data["result"], dict):
            result = progress_data["result"]
            if "document_id" in result and "id" not in result:
                result["id"] = result.pop("document_id")
        
        return TaskProgressData(**progress_data)
        
    except Exception as e:
        logger.error(f"Failed to get progress for task {task_id}: {e}", exc_info=True)
        # Return a safe default response instead of raising error
        return TaskProgressData(
            status="UNKNOWN",
            progress=0.0,
            stage="Error fetching progress",
            filename="Unknown"
        )

@router.get("/task-result/{task_id}", response_model=DocumentResponse)
async def get_task_result(task_id: str):
    """
    Get final document result once async processing is complete
    """
    try:
        from ..celery_app import celery_app
        
        task = celery_app.AsyncResult(task_id)
        
        if task.state == "PENDING" or task.state == "STARTED" or task.state == "RETRY":
            current_progress = ProgressTracker.get_progress(task_id)
            raise HTTPException(status_code=202, detail=f"Task is {task.state}. Stage: {current_progress.get('stage', 'N/A')}")
        elif task.state == "SUCCESS":
            result = task.result
            if not isinstance(result, dict):
                logger.error(f"Task {task_id} Succeeded but result is not a dict: {type(result)} - {result}")
                raise HTTPException(status_code=500, detail="Task succeeded but result format is unexpected.")
            
            return DocumentResponse(
                id=result.get("document_id", task_id),
                filename=result["filename"],
                content_type=result["content_type"],
                size=result["size"],
                chunk_count=result["chunk_count"],
                created_at=datetime.fromisoformat(result["created_at"]),
                metadata=result["metadata"]
            )
        elif task.state == "FAILURE":
            failure_progress = ProgressTracker.get_progress(task_id)
            error_info = failure_progress.get('error', str(task.info))
            raise HTTPException(status_code=500, detail=f"Processing failed: {error_info}")
        else:
            raise HTTPException(status_code=202, detail=f"Task status: {task.state}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task result for {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get task result for {task_id}: {str(e)}")

# ================================
# DOCUMENT MANAGEMENT ENDPOINTS
# ================================

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    client_id: Optional[str] = None,
    weaviate: WeaviateService = Depends(get_weaviate_service),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """Get paginated list of documents from Weaviate filtered by user's authorized clients"""
    try:
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=400, detail="Page size: 1-100")
        
        # Get user's accessible client IDs
        accessible_client_ids = await auth_context.auth_client.get_accessible_client_matters(
            auth_context.user_id, "read_docs"
        )
        
        # Check if user is admin (indicated by special marker)
        is_admin = "__ALL_CLIENTS__" in accessible_client_ids
        
        if is_admin:
            # Admin users see all documents - no filtering needed
            all_documents_result = await weaviate.list_documents(
                page=page,
                page_size=page_size
            )
            authorized_documents = all_documents_result.get("documents", [])
            total_authorized = all_documents_result.get("total", len(authorized_documents))
        else:
            # Add "all" to accessible clients (documents with no specific client assignment)
            accessible_client_ids.append("all")
            
            # Fetch all documents first, then filter by client access
            all_documents_result = await weaviate.list_documents(
                page=1,
                page_size=1000  # Get a large number to filter from
            )
            
            # Filter documents by accessible client IDs
            authorized_documents = []
            for doc_info in all_documents_result.get("documents", []):
                doc_metadata = doc_info.get("metadata", {})
                doc_client_id = doc_metadata.get("client_id", "all")
                
                # Check if user has access to this document's client
                if doc_client_id in accessible_client_ids:
                    authorized_documents.append(doc_info)
            
            # Apply pagination to filtered results
            total_authorized = len(authorized_documents)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            authorized_documents = authorized_documents[start_idx:end_idx]
        
        # Convert to API response format
        documents = []
        for doc_info in authorized_documents:
            doc_response = DocumentResponse(
                id=doc_info.get("id", "N/A"),
                filename=doc_info.get("filename", "Unknown"),
                content_type=doc_info.get("content_type", "N/A"),
                size=doc_info.get("size", 0),
                chunk_count=doc_info.get("chunk_count", 0),
                created_at=datetime.fromisoformat(doc_info["created_at"].replace("Z", "+00:00")) if doc_info.get("created_at") else datetime.utcnow(),
                metadata=doc_info.get("metadata", {})
            )
            documents.append(doc_response)
        
        response = DocumentListResponse(
            documents=documents,
            total=total_authorized,
            page=page,
            page_size=page_size
        )
        
        logger.info(f"Listed {len(documents)} documents (page {page})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    weaviate: WeaviateService = Depends(get_weaviate_service),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """Get information about a specific document"""
    try:
        doc_info = await weaviate.get_document_info(document_id)
        
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check authorization - get client_id from document metadata
        doc_metadata = doc_info.get("metadata", {})
        doc_client_id = doc_metadata.get("client_id", "all")
        
        # Verify user has access to this document's client
        has_access = await auth_context.auth_client.verify_access(
            auth_context.user_id, doc_client_id, "read_docs"
        )
        
        # Special case: allow access to "all" documents for any authenticated user
        if not has_access and doc_client_id != "all":
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: You do not have permission to access documents for client {doc_client_id}"
            )
        
        response = DocumentResponse(
            id=doc_info.get("id", document_id),
            filename=doc_info.get("filename", "Unknown"),
            content_type=doc_info.get("content_type", "N/A"),
            size=doc_info.get("size", 0),
            chunk_count=doc_info.get("chunk_count", 0),
            created_at=datetime.fromisoformat(doc_info["created_at"].replace("Z", "+00:00")) if doc_info.get("created_at") else datetime.utcnow(),
            metadata=doc_info.get("metadata", {})
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get document {document_id}: {str(e)}")

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    weaviate: WeaviateService = Depends(get_weaviate_service),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """Delete a document and its chunks from Weaviate"""
    try:
        # First check if document exists and get its metadata for authorization
        doc_info = await weaviate.get_document_info(document_id)
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check authorization - get client_id from document metadata
        doc_metadata = doc_info.get("metadata", {})
        doc_client_id = doc_metadata.get("client_id", "all")
        
        # Verify user has delete permissions for this document's client
        has_access = await auth_context.auth_client.verify_access(
            auth_context.user_id, doc_client_id, "delete_docs"
        )
        
        # Special case: allow deletion of "all" documents for any authenticated user (or admin only?)
        if not has_access and doc_client_id != "all":
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: You do not have permission to delete documents for client {doc_client_id}"
            )
        
        # Proceed with deletion
        success = await weaviate.delete_document(document_id)
        if not success:
            logger.warning(f"Attempt to delete document {document_id} reported failure or not found by service.")
            raise HTTPException(status_code=404, detail="Document not found or deletion failed.")
        
        logger.info(f"Document {document_id} deleted successfully.")
        return {"document_id": document_id, "status": "DELETED"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete document {document_id}: {str(e)}")

@router.get("/{document_id}/chunks", response_model=List[dict])
async def get_document_chunks(
    document_id: str,
    weaviate: WeaviateService = Depends(get_weaviate_service),
    auth_context: AuthContext = Depends(get_auth_context),
):
    try:
        # First check if document exists and get its metadata for authorization
        doc_info = await weaviate.get_document_info(document_id)
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check authorization - get client_id from document metadata
        doc_metadata = doc_info.get("metadata", {})
        doc_client_id = doc_metadata.get("client_id", "all")
        
        # Verify user has read permissions for this document's client
        has_access = await auth_context.auth_client.verify_access(
            auth_context.user_id, doc_client_id, "read_docs"
        )
        
        # Special case: allow access to "all" documents for any authenticated user
        if not has_access and doc_client_id != "all":
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: You do not have permission to access documents for client {doc_client_id}"
            )
        
        chunks = await weaviate.get_document_chunks(document_id)
        if chunks is None:
            raise HTTPException(status_code=404, detail="Document not found or has no chunks")
        return chunks
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chunks for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get chunks for document {document_id}: {str(e)}") 