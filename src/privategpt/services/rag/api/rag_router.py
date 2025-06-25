from __future__ import annotations

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.infra.database.async_session import get_async_session
from privategpt.infra.database.document_repository import SqlDocumentRepository
from privategpt.infra.database.collection_repository import CollectionRepository
from privategpt.core.domain.document import DocumentStatus, Document
from privategpt.core.domain.collection import Collection, CollectionSettings
from privategpt.core.domain.query import SearchQuery
from privategpt.infra.tasks.celery_app import app as celery_app  # noqa: E501
from privategpt.infra.tasks.service_factory import build_rag_service
from privategpt.infra.tasks.celery_queue import CeleryTaskQueueAdapter
from celery.result import AsyncResult

router = APIRouter(prefix="/rag", tags=["rag"])


# Collection Models
class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[str] = None
    icon: str = "📁"
    color: str = "#3B82F6"
    settings: Optional[Dict[str, Any]] = None


class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class CollectionMove(BaseModel):
    parent_id: Optional[str] = None


class CollectionOut(BaseModel):
    id: str
    user_id: int
    parent_id: Optional[str]
    name: str
    description: Optional[str]
    collection_type: str
    icon: str
    color: str
    path: str
    depth: int
    settings: Dict[str, Any]
    created_at: str
    updated_at: str
    document_count: Optional[int] = None
    total_document_count: Optional[int] = None


# Document Models
class DocumentIn(BaseModel):
    title: str = Field(...)
    text: str = Field(..., min_length=1)
    collection_id: Optional[str] = None


class DocumentOut(BaseModel):
    id: int
    title: str
    status: DocumentStatus
    error: str | None = None
    collection_id: Optional[str] = None


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    collection_ids: Optional[List[str]] = None
    include_subfolders: bool = True


class ChatAnswer(BaseModel):
    answer: str
    citations: list[dict]


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    data: DocumentIn, session: AsyncSession = Depends(get_async_session)
):
    repo = SqlDocumentRepository(session)
    import datetime as _dt

    new_doc = Document(
        id=None,
        title=data.title,
        file_path="memory",
        uploaded_at=_dt.datetime.utcnow(),
        status=DocumentStatus.PENDING,
    )
    doc = await repo.add(new_doc)
    task_queue = CeleryTaskQueueAdapter()
    task_id = task_queue.enqueue("ingest_document", doc.id, "memory", data.title, data.text)
    doc.task_id = task_id  # type: ignore[attr-defined]
    await repo.update(doc)
    return {"task_id": task_id, "document_id": doc.id}


@router.get("/documents/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: int, session: AsyncSession = Depends(get_async_session)):
    repo = SqlDocumentRepository(session)
    doc = await repo.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/documents/{doc_id}/status")
async def get_document_status(doc_id: int, session: AsyncSession = Depends(get_async_session)):
    """Get detailed processing status for a document."""
    repo = SqlDocumentRepository(session)
    doc = await repo.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get chunk count if processed
    chunk_count = 0
    if doc.status == DocumentStatus.COMPLETE:
        from privategpt.infra.database.chunk_repository import SqlChunkRepository
        chunk_repo = SqlChunkRepository(session)
        chunks = await chunk_repo.list_by_document(doc_id)
        chunk_count = len(chunks)
    
    return {
        "document_id": doc.id,
        "title": doc.title,
        "status": doc.status,
        "error": doc.error,
        "task_id": doc.task_id,
        "processing_progress": doc.processing_progress,
        "chunk_count": chunk_count,
        "collection_id": doc.collection_id,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
    }


@router.get("/progress/{task_id}")
def task_progress(task_id: str):
    """Get detailed progress information for a document processing task."""
    res: AsyncResult = celery_app.AsyncResult(task_id)
    
    if res.state == 'PENDING':
        return {
            "state": res.state,
            "progress": 0,
            "stage": "pending",
            "message": "Task is waiting to be processed"
        }
    elif res.state == 'PROGRESS':
        return {
            "state": res.state,
            "progress": res.info.get('progress', 0),
            "stage": res.info.get('stage', 'unknown'),
            "message": res.info.get('message', ''),
            "document_id": res.info.get('document_id'),
            "title": res.info.get('title')
        }
    elif res.state == 'SUCCESS':
        return {
            "state": res.state,
            "progress": 100,
            "stage": "complete",
            "message": "Document processing completed successfully",
            "result": res.result
        }
    elif res.state == 'FAILURE':
        return {
            "state": res.state,
            "progress": 0,
            "stage": "failed",
            "message": "Document processing failed",
            "error": str(res.info)
        }
    else:
        return {
            "state": res.state,
            "progress": 0,
            "stage": res.state.lower(),
            "info": res.info
        }


@router.post("/chat", response_model=ChatAnswer)
async def rag_chat(req: ChatRequest, session: AsyncSession = Depends(get_async_session)):
    rag = build_rag_service(session)
    ans = await rag.chat(req.question)
    return {"answer": ans.text, "citations": ans.citations}


# Helper function to get user ID (placeholder for now)
def get_current_user_id(request: Request) -> int:
    """Extract user ID from request. For now, return test user ID."""
    # TODO: Extract from JWT token in auth middleware
    return 1


# Test endpoint to create test user
@router.post("/test/create-user", include_in_schema=False)
async def create_test_user(session: AsyncSession = Depends(get_async_session)):
    """Create test user for development."""
    from privategpt.infra.database.models import User
    from sqlalchemy import select
    
    # Check if user exists
    result = await session.execute(select(User).where(User.id == 1))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        return {"message": "Test user already exists", "user_id": 1}
    
    # Create test user
    test_user = User(
        id=1,
        email="test@example.com",
        role="user",
        is_active=True
    )
    session.add(test_user)
    await session.commit()
    
    return {"message": "Test user created", "user_id": 1}


def _collection_to_out(collection: Collection, document_count: int = None, total_document_count: int = None) -> CollectionOut:
    """Convert domain model to API response model."""
    return CollectionOut(
        id=collection.id,
        user_id=collection.user_id,
        parent_id=collection.parent_id,
        name=collection.name,
        description=collection.description,
        collection_type=collection.collection_type,
        icon=collection.icon,
        color=collection.color,
        path=collection.path,
        depth=collection.depth,
        settings=collection.settings or {},
        created_at=collection.created_at.isoformat() if collection.created_at else "",
        updated_at=collection.updated_at.isoformat() if collection.updated_at else "",
        document_count=document_count,
        total_document_count=total_document_count
    )


# Collection Endpoints

@router.post("/collections", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
async def create_collection(
    data: CollectionCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new collection or folder."""
    user_id = get_current_user_id(request)
    repo = CollectionRepository(session)
    
    # Parse settings if provided
    settings = None
    if data.settings:
        settings = CollectionSettings.from_dict(data.settings)
    
    collection = Collection(
        user_id=user_id,
        parent_id=data.parent_id,
        name=data.name,
        description=data.description,
        icon=data.icon,
        color=data.color,
        settings=settings
    )
    
    try:
        created_collection = await repo.create(collection)
        return _collection_to_out(created_collection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")


@router.get("/collections", response_model=List[CollectionOut])
async def list_root_collections(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """List root collections for the current user."""
    user_id = get_current_user_id(request)
    repo = CollectionRepository(session)
    
    collections = await repo.list_roots(user_id)
    result = []
    
    for collection in collections:
        doc_count = await repo.count_documents(collection.id)
        total_doc_count = await repo.count_all_documents(collection.id)
        result.append(_collection_to_out(collection, doc_count, total_doc_count))
    
    return result


@router.get("/collections/{collection_id}", response_model=CollectionOut)
async def get_collection(
    collection_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Get collection by ID."""
    repo = CollectionRepository(session)
    collection = await repo.get_by_id(collection_id)
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    doc_count = await repo.count_documents(collection_id)
    total_doc_count = await repo.count_all_documents(collection_id)
    return _collection_to_out(collection, doc_count, total_doc_count)


@router.get("/collections/{collection_id}/children", response_model=List[CollectionOut])
async def list_collection_children(
    collection_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """List child collections/folders."""
    repo = CollectionRepository(session)
    
    # Verify parent exists
    parent = await repo.get_by_id(collection_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent collection not found")
    
    children = await repo.list_children(collection_id)
    result = []
    
    for child in children:
        doc_count = await repo.count_documents(child.id)
        total_doc_count = await repo.count_all_documents(child.id)
        result.append(_collection_to_out(child, doc_count, total_doc_count))
    
    return result


@router.get("/collections/{collection_id}/path", response_model=List[CollectionOut])
async def get_collection_breadcrumb_path(
    collection_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Get breadcrumb path from root to collection."""
    repo = CollectionRepository(session)
    path = await repo.get_breadcrumb_path(collection_id)
    
    if not path:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    return [_collection_to_out(collection) for collection in path]


@router.patch("/collections/{collection_id}", response_model=CollectionOut)
async def update_collection(
    collection_id: str,
    data: CollectionUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """Update collection properties."""
    repo = CollectionRepository(session)
    
    # Build updates dict
    updates = {}
    if data.name is not None:
        updates["name"] = data.name
    if data.description is not None:
        updates["description"] = data.description
    if data.icon is not None:
        updates["icon"] = data.icon
    if data.color is not None:
        updates["color"] = data.color
    if data.settings is not None:
        updates["settings"] = CollectionSettings.from_dict(data.settings)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    try:
        updated_collection = await repo.update(collection_id, updates)
        if not updated_collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        return _collection_to_out(updated_collection)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update collection: {str(e)}")


@router.post("/collections/{collection_id}/move", response_model=CollectionOut)
async def move_collection(
    collection_id: str,
    data: CollectionMove,
    session: AsyncSession = Depends(get_async_session)
):
    """Move collection to a different parent."""
    repo = CollectionRepository(session)
    
    try:
        moved_collection = await repo.move(collection_id, data.parent_id)
        if not moved_collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        return _collection_to_out(moved_collection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to move collection: {str(e)}")


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: str,
    hard_delete: bool = False,
    session: AsyncSession = Depends(get_async_session)
):
    """Delete collection (soft delete by default)."""
    repo = CollectionRepository(session)
    
    # Check if collection exists
    collection = await repo.get_by_id(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    try:
        await repo.delete(collection_id, hard_delete)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete collection: {str(e)}")


# Update existing document upload to support collections
@router.post("/collections/{collection_id}/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_document_to_collection(
    collection_id: str,
    data: DocumentIn,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """Upload document to a specific collection."""
    user_id = get_current_user_id(request)
    
    # Verify collection exists and belongs to user
    collection_repo = CollectionRepository(session)
    collection = await collection_repo.get_by_id(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    if collection.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create document with collection
    repo = SqlDocumentRepository(session)
    import datetime as _dt

    new_doc = Document(
        id=None,
        collection_id=collection_id,
        user_id=user_id,
        title=data.title,
        file_path="memory",
        uploaded_at=_dt.datetime.utcnow(),
        status=DocumentStatus.PENDING,
    )
    doc = await repo.add(new_doc)
    task_queue = CeleryTaskQueueAdapter()
    task_id = task_queue.enqueue("ingest_document", doc.id, "memory", data.title, data.text)
    doc.task_id = task_id  # type: ignore[attr-defined]
    await repo.update(doc)
    return {"task_id": task_id, "document_id": doc.id, "collection_id": collection_id} 