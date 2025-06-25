"""Tests for RAG API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json

from privategpt.services.rag.api.app import app
from privategpt.core.domain.collection import Collection
from privategpt.core.domain.document import Document, DocumentStatus
from privategpt.infra.database.models import User


@pytest.fixture
def client():
    """Provide test client."""
    return TestClient(app)


@pytest.fixture
def mock_session():
    """Mock database session."""
    with patch('privategpt.services.rag.api.rag_router.get_async_session') as mock:
        session = AsyncMock()
        mock.return_value.__aenter__.return_value = session
        yield session


@pytest.fixture
def test_user():
    """Mock test user."""
    user = User(id=1, email="test@example.com", role="user", is_active=True)
    return user


def test_create_collection(client, mock_session):
    """Test creating a collection via API."""
    # Mock repository
    with patch('privategpt.services.rag.api.rag_router.SqlCollectionRepository') as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.add = AsyncMock(return_value=Collection(
            id="test-id",
            user_id=1,
            parent_id=None,
            name="Test Collection",
            description="Test description",
            icon="📁",
            color="#3B82F6"
        ))
        
        response = client.post("/collections", json={
            "name": "Test Collection",
            "description": "Test description",
            "icon": "📁",
            "color": "#3B82F6"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Collection"
        assert data["icon"] == "📁"


def test_list_collections(client, mock_session):
    """Test listing collections."""
    with patch('privategpt.services.rag.api.rag_router.SqlCollectionRepository') as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.list_by_user = AsyncMock(return_value=[
            Collection(
                id="coll-1",
                user_id=1,
                parent_id=None,
                name="Collection 1"
            ),
            Collection(
                id="coll-2",
                user_id=1,
                parent_id=None,
                name="Collection 2"
            )
        ])
        
        # Mock document count
        with patch('privategpt.services.rag.api.rag_router.SqlDocumentRepository') as mock_doc_repo_class:
            mock_doc_repo = mock_doc_repo_class.return_value
            mock_doc_repo.count_by_collection = AsyncMock(return_value=0)
            
            response = client.get("/collections")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "Collection 1"
            assert data[1]["name"] == "Collection 2"


def test_upload_document(client, mock_session):
    """Test uploading a document to a collection."""
    collection_id = "test-collection-id"
    
    with patch('privategpt.services.rag.api.rag_router.SqlDocumentRepository') as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.add = AsyncMock(return_value=Document(
            id=1,
            collection_id=collection_id,
            user_id=1,
            title="Test Document",
            file_path="/tmp/test.txt",
            file_name="test.txt",
            file_size=1000,
            mime_type="text/plain",
            status=DocumentStatus.PENDING,
            task_id="task-123"
        ))
        
        with patch('privategpt.infra.tasks.celery_app.ingest_document_task.delay') as mock_task:
            mock_task.return_value = Mock(id="task-123")
            
            response = client.post(f"/collections/{collection_id}/documents", json={
                "title": "Test Document",
                "text": "This is test content"
            })
            
            assert response.status_code == 202
            data = response.json()
            assert data["document_id"] == 1
            assert data["task_id"] == "task-123"
            assert data["status"] == "pending"


def test_get_task_progress(client):
    """Test getting task progress."""
    task_id = "test-task-123"
    
    with patch('privategpt.services.rag.api.rag_router.celery_app.AsyncResult') as mock_result:
        mock_async_result = Mock()
        mock_async_result.state = 'PROGRESS'
        mock_async_result.info = {
            'stage': 'embedding',
            'progress': 65,
            'message': 'Processing chunk 20/30',
            'document_id': 1,
            'title': 'Test Doc'
        }
        mock_result.return_value = mock_async_result
        
        response = client.get(f"/progress/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "PROGRESS"
        assert data["stage"] == "embedding"
        assert data["progress"] == 65
        assert data["message"] == "Processing chunk 20/30"


def test_get_document_status(client, mock_session):
    """Test getting document status."""
    doc_id = 1
    
    with patch('privategpt.services.rag.api.rag_router.SqlDocumentRepository') as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_by_id = AsyncMock(return_value=Document(
            id=doc_id,
            collection_id="coll-1",
            user_id=1,
            title="Processed Document",
            file_path="/tmp/doc.txt",
            file_name="doc.txt",
            file_size=2000,
            mime_type="text/plain",
            status=DocumentStatus.COMPLETE,
            task_id="task-456",
            processing_progress={"chunks": 15, "stage": "complete"}
        ))
        
        with patch('privategpt.services.rag.api.rag_router.SqlChunkRepository') as mock_chunk_class:
            mock_chunk_repo = mock_chunk_class.return_value
            mock_chunk_repo.list_by_document = AsyncMock(return_value=[Mock() for _ in range(15)])
            
            response = client.get(f"/documents/{doc_id}/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == doc_id
            assert data["title"] == "Processed Document"
            assert data["status"] == "complete"
            assert data["chunk_count"] == 15


def test_collection_breadcrumb(client, mock_session):
    """Test getting collection breadcrumb."""
    collection_id = "child-collection"
    
    with patch('privategpt.services.rag.api.rag_router.SqlCollectionRepository') as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_breadcrumb = AsyncMock(return_value=[
            Collection(id="root", user_id=1, parent_id=None, name="Root"),
            Collection(id="parent", user_id=1, parent_id="root", name="Parent"),
            Collection(id="child-collection", user_id=1, parent_id="parent", name="Child")
        ])
        
        response = client.get(f"/collections/{collection_id}/breadcrumb")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["name"] == "Root"
        assert data[1]["name"] == "Parent"
        assert data[2]["name"] == "Child"


def test_chat_endpoint(client):
    """Test chat endpoint."""
    with patch('privategpt.services.rag.api.rag_router.build_rag_service') as mock_build:
        mock_service = Mock()
        mock_service.chat = AsyncMock(return_value=Mock(
            text="Based on the documents, the answer is...",
            citations=[
                {"chunk_id": "chunk-1", "score": 0.95},
                {"chunk_id": "chunk-2", "score": 0.87}
            ]
        ))
        mock_build.return_value = mock_service
        
        response = client.post("/chat", json={
            "question": "What is the main topic?"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "Based on the documents" in data["answer"]
        assert len(data["citations"]) == 2


def test_delete_collection(client, mock_session):
    """Test deleting a collection."""
    collection_id = "to-delete"
    
    with patch('privategpt.services.rag.api.rag_router.SqlCollectionRepository') as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_by_id = AsyncMock(return_value=Collection(
            id=collection_id,
            user_id=1,
            parent_id=None,
            name="To Delete"
        ))
        mock_repo.delete = AsyncMock()
        
        with patch('privategpt.services.rag.api.rag_router.SqlDocumentRepository') as mock_doc_class:
            mock_doc_repo = mock_doc_class.return_value
            mock_doc_repo.delete_by_collection = AsyncMock()
            
            response = client.delete(f"/collections/{collection_id}?hard_delete=true")
            
            assert response.status_code == 204
            mock_repo.delete.assert_called_once_with(collection_id)
            mock_doc_repo.delete_by_collection.assert_called_once()


def test_update_collection(client, mock_session):
    """Test updating a collection."""
    collection_id = "to-update"
    
    with patch('privategpt.services.rag.api.rag_router.SqlCollectionRepository') as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_by_id = AsyncMock(return_value=Collection(
            id=collection_id,
            user_id=1,
            parent_id=None,
            name="Old Name",
            description="Old description"
        ))
        mock_repo.update = AsyncMock(return_value=Collection(
            id=collection_id,
            user_id=1,
            parent_id=None,
            name="New Name",
            description="New description",
            icon="🆕"
        ))
        
        response = client.patch(f"/collections/{collection_id}", json={
            "name": "New Name",
            "description": "New description",
            "icon": "🆕"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "New description"
        assert data["icon"] == "🆕"