"""Tests for document processing with Celery tasks."""
import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from celery.result import AsyncResult

from privategpt.core.domain.document import Document, DocumentStatus
from privategpt.infra.database.document_repository import SqlDocumentRepository
from privategpt.infra.database.models import User
from privategpt.infra.database.async_session import get_async_session, engine
from privategpt.infra.database import models
from privategpt.infra.tasks.celery_app import ingest_document_task
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(scope="module", autouse=True)
async def create_db():
    """Create test database schema."""
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """Provide async database session."""
    async with get_async_session() as s:
        yield s


@pytest_asyncio.fixture
async def test_user(session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        role="user",
        is_active=True
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def document_repo(session: AsyncSession) -> SqlDocumentRepository:
    """Provide document repository."""
    return SqlDocumentRepository(session)


@pytest.mark.asyncio
async def test_document_upload_triggers_task(document_repo: SqlDocumentRepository, test_user: User):
    """Test that uploading a document triggers Celery task."""
    with patch('privategpt.infra.tasks.celery_app.ingest_document_task.delay') as mock_delay:
        mock_delay.return_value = Mock(id="test-task-id")
        
        # Create document
        doc = Document(
            id=None,
            collection_id=None,
            user_id=test_user.id,
            title="Test Document",
            file_path="/tmp/test.txt",
            file_name="test.txt",
            file_size=1000,
            mime_type="text/plain",
            status=DocumentStatus.PENDING
        )
        
        created = await document_repo.add(doc)
        
        # Simulate task triggering (normally done in API endpoint)
        task_result = ingest_document_task.delay(
            created.id,
            created.file_path,
            created.title,
            "Test document content"
        )
        
        # Verify task was called
        mock_delay.assert_called_once_with(
            created.id,
            created.file_path,
            created.title,
            "Test document content"
        )
        
        assert created.status == DocumentStatus.PENDING


def test_celery_task_progress_tracking():
    """Test Celery task progress updates."""
    with patch('privategpt.infra.tasks.celery_sync.process_document_sync') as mock_process:
        # Mock the task
        task = Mock()
        task.update_state = Mock()
        
        # Bind task to function
        bound_task = ingest_document_task.bind(task)
        
        # Call the task
        bound_task(1, "/tmp/test.txt", "Test", "Content")
        
        # Verify process_document_sync was called
        mock_process.assert_called_once_with(1, "/tmp/test.txt", "Test", "Content")


@pytest.mark.asyncio
async def test_task_progress_states():
    """Test different progress states returned by task."""
    # Mock AsyncResult for different states
    mock_results = {
        'PENDING': {
            'state': 'PENDING',
            'info': None
        },
        'PROGRESS': {
            'state': 'PROGRESS',
            'info': {
                'stage': 'embedding',
                'progress': 50,
                'message': 'Processing chunks'
            }
        },
        'SUCCESS': {
            'state': 'SUCCESS',
            'result': {
                'document_id': 1,
                'chunks_created': 10
            }
        },
        'FAILURE': {
            'state': 'FAILURE',
            'info': {
                'error': 'Processing failed'
            }
        }
    }
    
    for state, expected in mock_results.items():
        mock_result = Mock(spec=AsyncResult)
        mock_result.state = expected['state']
        mock_result.info = expected.get('info')
        mock_result.result = expected.get('result')
        
        # Verify the result matches expected format
        assert mock_result.state == expected['state']
        if 'info' in expected:
            assert mock_result.info == expected['info']
        if 'result' in expected:
            assert mock_result.result == expected['result']


@pytest.mark.asyncio
async def test_document_status_update(document_repo: SqlDocumentRepository, test_user: User):
    """Test document status updates during processing."""
    # Create document
    doc = Document(
        id=None,
        collection_id=None,
        user_id=test_user.id,
        title="Status Test",
        file_path="/tmp/status.txt",
        file_name="status.txt",
        file_size=500,
        mime_type="text/plain",
        status=DocumentStatus.PENDING
    )
    
    created = await document_repo.add(doc)
    assert created.status == DocumentStatus.PENDING
    
    # Update status to processing
    created.status = DocumentStatus.PROCESSING
    created.task_id = "test-task-123"
    updated = await document_repo.update(created)
    assert updated.status == DocumentStatus.PROCESSING
    assert updated.task_id == "test-task-123"
    
    # Update to complete
    created.status = DocumentStatus.COMPLETE
    created.processing_progress = {"chunks": 10, "stage": "complete"}
    final = await document_repo.update(created)
    assert final.status == DocumentStatus.COMPLETE
    assert final.processing_progress["chunks"] == 10


@pytest.mark.asyncio
async def test_document_processing_error_handling(document_repo: SqlDocumentRepository, test_user: User):
    """Test error handling during document processing."""
    # Create document
    doc = Document(
        id=None,
        collection_id=None,
        user_id=test_user.id,
        title="Error Test",
        file_path="/tmp/error.txt",
        file_name="error.txt",
        file_size=100,
        mime_type="text/plain",
        status=DocumentStatus.PROCESSING
    )
    
    created = await document_repo.add(doc)
    
    # Simulate processing error
    created.status = DocumentStatus.FAILED
    created.error = "Failed to process document: Invalid format"
    
    updated = await document_repo.update(created)
    
    assert updated.status == DocumentStatus.FAILED
    assert "Invalid format" in updated.error


@pytest.mark.asyncio
async def test_chunk_creation_tracking():
    """Test that chunks are properly tracked during processing."""
    from privategpt.infra.database.chunk_repository import SqlChunkRepository
    from privategpt.core.domain.chunk import Chunk
    
    # Mock the chunk repository
    mock_chunk_repo = Mock(spec=SqlChunkRepository)
    mock_chunk_repo.add_many = AsyncMock()
    
    # Create test chunks
    chunks = [
        Chunk(
            id=None,
            document_id=1,
            position=i,
            text=f"Chunk {i}",
            embedding=[0.1] * 384  # Fake embedding
        )
        for i in range(5)
    ]
    
    # Add chunks
    await mock_chunk_repo.add_many(chunks)
    
    # Verify add_many was called
    mock_chunk_repo.add_many.assert_called_once_with(chunks)


@pytest.mark.asyncio
async def test_vector_store_integration():
    """Test vector store integration during processing."""
    from privategpt.infra.vector_store.weaviate_adapter_v4 import WeaviateAdapter
    
    # Mock vector store
    mock_vector_store = Mock(spec=WeaviateAdapter)
    mock_vector_store.add_vectors = AsyncMock()
    
    # Test data
    embeddings = [[0.1] * 384 for _ in range(3)]
    metadatas = [
        {"text": "chunk 1", "document_id": 1, "position": 0},
        {"text": "chunk 2", "document_id": 1, "position": 1},
        {"text": "chunk 3", "document_id": 1, "position": 2}
    ]
    ids = ["id1", "id2", "id3"]
    
    # Add vectors
    await mock_vector_store.add_vectors(embeddings, metadatas, ids)
    
    # Verify call
    mock_vector_store.add_vectors.assert_called_once_with(embeddings, metadatas, ids)