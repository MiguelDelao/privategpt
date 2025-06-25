"""Tests for collection management functionality."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from privategpt.core.domain.collection import Collection
from privategpt.core.domain.document import Document, DocumentStatus
from privategpt.infra.database.collection_repository import SqlCollectionRepository
from privategpt.infra.database.document_repository import SqlDocumentRepository
from privategpt.infra.database.models import User, Collection as CollectionModel
from privategpt.infra.database.async_session import get_async_session, engine
from privategpt.infra.database import models


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
async def collection_repo(session: AsyncSession) -> SqlCollectionRepository:
    """Provide collection repository."""
    return SqlCollectionRepository(session)


@pytest_asyncio.fixture
async def document_repo(session: AsyncSession) -> SqlDocumentRepository:
    """Provide document repository."""
    return SqlDocumentRepository(session)


@pytest.mark.asyncio
async def test_create_collection(collection_repo: SqlCollectionRepository, test_user: User):
    """Test creating a new collection."""
    collection = Collection(
        id=None,
        user_id=test_user.id,
        parent_id=None,
        name="Test Collection",
        description="A test collection",
        icon="📁",
        color="#3B82F6"
    )
    
    created = await collection_repo.add(collection)
    
    assert created.id is not None
    assert created.name == "Test Collection"
    assert created.description == "A test collection"
    assert created.icon == "📁"
    assert created.color == "#3B82F6"
    assert created.user_id == test_user.id


@pytest.mark.asyncio
async def test_nested_collections(collection_repo: SqlCollectionRepository, test_user: User):
    """Test creating nested collections."""
    # Create parent
    parent = await collection_repo.add(Collection(
        id=None,
        user_id=test_user.id,
        parent_id=None,
        name="Parent Collection"
    ))
    
    # Create child
    child = await collection_repo.add(Collection(
        id=None,
        user_id=test_user.id,
        parent_id=parent.id,
        name="Child Collection"
    ))
    
    # Verify relationship
    assert child.parent_id == parent.id
    
    # Get by ID
    retrieved = await collection_repo.get_by_id(child.id)
    assert retrieved is not None
    assert retrieved.parent_id == parent.id


@pytest.mark.asyncio
async def test_list_user_collections(collection_repo: SqlCollectionRepository, test_user: User):
    """Test listing collections for a user."""
    # Create multiple collections
    names = ["Collection A", "Collection B", "Collection C"]
    for name in names:
        await collection_repo.add(Collection(
            id=None,
            user_id=test_user.id,
            parent_id=None,
            name=name
        ))
    
    # List collections
    collections = await collection_repo.list_by_user(test_user.id)
    
    assert len(collections) >= 3
    collection_names = [c.name for c in collections]
    for name in names:
        assert name in collection_names


@pytest.mark.asyncio
async def test_update_collection(collection_repo: SqlCollectionRepository, test_user: User):
    """Test updating a collection."""
    # Create collection
    collection = await collection_repo.add(Collection(
        id=None,
        user_id=test_user.id,
        parent_id=None,
        name="Original Name",
        description="Original description"
    ))
    
    # Update it
    collection.name = "Updated Name"
    collection.description = "Updated description"
    collection.icon = "🔄"
    
    updated = await collection_repo.update(collection)
    
    assert updated.name == "Updated Name"
    assert updated.description == "Updated description"
    assert updated.icon == "🔄"


@pytest.mark.asyncio
async def test_delete_collection(collection_repo: SqlCollectionRepository, test_user: User):
    """Test deleting a collection."""
    # Create collection
    collection = await collection_repo.add(Collection(
        id=None,
        user_id=test_user.id,
        parent_id=None,
        name="To Delete"
    ))
    
    # Delete it
    await collection_repo.delete(collection.id)
    
    # Verify it's gone
    retrieved = await collection_repo.get_by_id(collection.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_collection_with_documents(
    collection_repo: SqlCollectionRepository,
    document_repo: SqlDocumentRepository,
    test_user: User,
    session: AsyncSession
):
    """Test collection with documents."""
    # Create collection
    collection = await collection_repo.add(Collection(
        id=None,
        user_id=test_user.id,
        parent_id=None,
        name="Document Collection"
    ))
    
    # Add documents to collection
    doc_titles = ["Doc 1", "Doc 2", "Doc 3"]
    for title in doc_titles:
        doc = Document(
            id=None,
            collection_id=collection.id,
            user_id=test_user.id,
            title=title,
            file_path=f"/tmp/{title}.txt",
            file_name=f"{title}.txt",
            file_size=1000,
            mime_type="text/plain",
            status=DocumentStatus.COMPLETE
        )
        await document_repo.add(doc)
    
    # Get collection with document count
    result = await session.execute(
        select(CollectionModel).where(CollectionModel.id == collection.id)
    )
    coll_model = result.scalar_one()
    
    # Verify documents exist
    docs = await document_repo.list_by_collection(collection.id)
    assert len(docs) == 3


@pytest.mark.asyncio
async def test_collection_breadcrumb(collection_repo: SqlCollectionRepository, test_user: User):
    """Test getting collection breadcrumb path."""
    # Create hierarchy: Root > Level1 > Level2
    root = await collection_repo.add(Collection(
        id=None,
        user_id=test_user.id,
        parent_id=None,
        name="Root"
    ))
    
    level1 = await collection_repo.add(Collection(
        id=None,
        user_id=test_user.id,
        parent_id=root.id,
        name="Level1"
    ))
    
    level2 = await collection_repo.add(Collection(
        id=None,
        user_id=test_user.id,
        parent_id=level1.id,
        name="Level2"
    ))
    
    # Get breadcrumb for level2
    breadcrumb = await collection_repo.get_breadcrumb(level2.id)
    
    assert len(breadcrumb) == 3
    assert breadcrumb[0].name == "Root"
    assert breadcrumb[1].name == "Level1"
    assert breadcrumb[2].name == "Level2"


@pytest.mark.asyncio
async def test_move_collection(collection_repo: SqlCollectionRepository, test_user: User):
    """Test moving a collection to a different parent."""
    # Create collections
    parent1 = await collection_repo.add(Collection(
        id=None,
        user_id=test_user.id,
        parent_id=None,
        name="Parent 1"
    ))
    
    parent2 = await collection_repo.add(Collection(
        id=None,
        user_id=test_user.id,
        parent_id=None,
        name="Parent 2"
    ))
    
    child = await collection_repo.add(Collection(
        id=None,
        user_id=test_user.id,
        parent_id=parent1.id,
        name="Child"
    ))
    
    # Move child from parent1 to parent2
    child.parent_id = parent2.id
    updated = await collection_repo.update(child)
    
    assert updated.parent_id == parent2.id
    
    # Verify breadcrumb updated
    breadcrumb = await collection_repo.get_breadcrumb(child.id)
    assert len(breadcrumb) == 2
    assert breadcrumb[0].name == "Parent 2"
    assert breadcrumb[1].name == "Child"