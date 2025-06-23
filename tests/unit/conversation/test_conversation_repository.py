"""
Unit tests for conversation repository.

Tests the core database operations for conversations including
SQLAlchemy async session handling, CRUD operations, and
the context manager pattern that was implemented to fix
MissingGreenlet errors.
"""

import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload

from privategpt.core.domain.conversation import Conversation as DomainConversation
from privategpt.core.domain.message import Message as DomainMessage
from privategpt.infra.database.conversation_repository import SqlConversationRepository
from privategpt.infra.database.models import Conversation, Message, MessageRole, User, Base


@pytest_asyncio.fixture
async def async_session():
    """Create an async test session using SQLite in-memory database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    from sqlalchemy.ext.asyncio import async_sessionmaker
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Create a test user
        test_user = User(
            id=1,
            keycloak_id="test-user-123",
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            role="user",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(test_user)
        await session.commit()
        
        yield session
    
    await engine.dispose()


@pytest_asyncio.fixture
async def conversation_repo(async_session):
    """Create conversation repository with test session."""
    return SqlConversationRepository(async_session)


@pytest_asyncio.fixture
async def sample_conversation():
    """Create a sample domain conversation for testing."""
    return DomainConversation(
        id=str(uuid4()),
        user_id=1,
        title="Test Conversation",
        status="active",
        model_name="test-model",
        system_prompt="You are a helpful assistant",
        data={"test": "data"},
        messages=[],
        total_tokens=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestConversationCRUD:
    """Test basic CRUD operations for conversations."""
    
    @pytest_asyncio.async_test
    async def test_create_conversation(self, conversation_repo, sample_conversation):
        """Test creating a new conversation."""
        # Act
        created = await conversation_repo.create(sample_conversation)
        
        # Assert
        assert created.id == sample_conversation.id
        assert created.title == sample_conversation.title
        assert created.user_id == sample_conversation.user_id
        assert created.status == "active"
        assert created.model_name == "test-model"
        assert created.system_prompt == "You are a helpful assistant"
        assert created.data == {"test": "data"}
        assert created.total_tokens == 0
        assert len(created.messages) == 0
    
    @pytest_asyncio.async_test
    async def test_get_conversation_by_id(self, conversation_repo, sample_conversation):
        """Test retrieving a conversation by ID."""
        # Arrange
        created = await conversation_repo.create(sample_conversation)
        
        # Act
        retrieved = await conversation_repo.get(created.id)
        
        # Assert
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == created.title
        assert retrieved.user_id == created.user_id
    
    @pytest_asyncio.async_test
    async def test_get_nonexistent_conversation(self, conversation_repo):
        """Test retrieving a conversation that doesn't exist."""
        # Act
        result = await conversation_repo.get("nonexistent-id")
        
        # Assert
        assert result is None
    
    @pytest_asyncio.async_test
    async def test_update_conversation(self, conversation_repo, sample_conversation):
        """Test updating an existing conversation."""
        # Arrange
        created = await conversation_repo.create(sample_conversation)
        created.title = "Updated Title"
        created.status = "archived"
        created.updated_at = datetime.utcnow()
        
        # Act
        updated = await conversation_repo.update(created)
        
        # Assert
        assert updated.title == "Updated Title"
        assert updated.status == "archived"
        assert updated.id == created.id
    
    @pytest_asyncio.async_test
    async def test_update_nonexistent_conversation(self, conversation_repo, sample_conversation):
        """Test updating a conversation that doesn't exist."""
        # Arrange
        sample_conversation.id = "nonexistent-id"
        
        # Act & Assert
        with pytest.raises(ValueError, match="Conversation nonexistent-id not found"):
            await conversation_repo.update(sample_conversation)
    
    @pytest_asyncio.async_test
    async def test_delete_conversation(self, conversation_repo, sample_conversation):
        """Test soft deleting a conversation."""
        # Arrange
        created = await conversation_repo.create(sample_conversation)
        
        # Act
        result = await conversation_repo.delete(created.id)
        
        # Assert
        assert result is True
        
        # Verify conversation is marked as deleted
        retrieved = await conversation_repo.get(created.id)
        assert retrieved is not None
        assert retrieved.status == "deleted"
    
    @pytest_asyncio.async_test
    async def test_delete_nonexistent_conversation(self, conversation_repo):
        """Test deleting a conversation that doesn't exist."""
        # Act
        result = await conversation_repo.delete("nonexistent-id")
        
        # Assert
        assert result is False


class TestConversationQueries:
    """Test conversation query operations."""
    
    @pytest_asyncio.async_test
    async def test_get_conversations_by_user(self, conversation_repo, async_session):
        """Test retrieving conversations for a specific user."""
        # Arrange - Create multiple conversations
        conversations = []
        for i in range(3):
            conv = DomainConversation(
                id=str(uuid4()),
                user_id=1,
                title=f"Conversation {i}",
                status="active",
                model_name="test-model",
                system_prompt=None,
                data={},
                messages=[],
                total_tokens=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            conversations.append(await conversation_repo.create(conv))
        
        # Act
        user_conversations = await conversation_repo.get_by_user(user_id=1, limit=10, offset=0)
        
        # Assert
        assert len(user_conversations) == 3
        for conv in user_conversations:
            assert conv.user_id == 1
            assert conv.status != "deleted"
    
    @pytest_asyncio.async_test
    async def test_get_conversations_excludes_deleted(self, conversation_repo):
        """Test that get_by_user excludes deleted conversations."""
        # Arrange
        active_conv = DomainConversation(
            id=str(uuid4()),
            user_id=1,
            title="Active Conversation",
            status="active",
            model_name="test-model",
            system_prompt=None,
            data={},
            messages=[],
            total_tokens=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        deleted_conv = DomainConversation(
            id=str(uuid4()),
            user_id=1,
            title="Deleted Conversation",
            status="deleted",
            model_name="test-model",
            system_prompt=None,
            data={},
            messages=[],
            total_tokens=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await conversation_repo.create(active_conv)
        await conversation_repo.create(deleted_conv)
        
        # Act
        user_conversations = await conversation_repo.get_by_user(user_id=1)
        
        # Assert
        assert len(user_conversations) == 1
        assert user_conversations[0].title == "Active Conversation"
    
    @pytest_asyncio.async_test
    async def test_get_conversations_pagination(self, conversation_repo):
        """Test pagination in get_by_user."""
        # Arrange - Create 5 conversations
        for i in range(5):
            conv = DomainConversation(
                id=str(uuid4()),
                user_id=1,
                title=f"Conversation {i}",
                status="active",
                model_name="test-model",
                system_prompt=None,
                data={},
                messages=[],
                total_tokens=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await conversation_repo.create(conv)
        
        # Act - Get first page
        page1 = await conversation_repo.get_by_user(user_id=1, limit=2, offset=0)
        page2 = await conversation_repo.get_by_user(user_id=1, limit=2, offset=2)
        
        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        # Ensure different conversations on different pages
        page1_ids = {conv.id for conv in page1}
        page2_ids = {conv.id for conv in page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    @pytest_asyncio.async_test
    async def test_search_conversations(self, conversation_repo):
        """Test searching conversations by title and content."""
        # Arrange
        searchable_conv = DomainConversation(
            id=str(uuid4()),
            user_id=1,
            title="Python Programming Help",
            status="active",
            model_name="test-model",
            system_prompt=None,
            data={},
            messages=[],
            total_tokens=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        other_conv = DomainConversation(
            id=str(uuid4()),
            user_id=1,
            title="JavaScript Development",
            status="active",
            model_name="test-model",
            system_prompt=None,
            data={},
            messages=[],
            total_tokens=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await conversation_repo.create(searchable_conv)
        await conversation_repo.create(other_conv)
        
        # Act
        results = await conversation_repo.search(user_id=1, query="Python", limit=10)
        
        # Assert
        assert len(results) == 1
        assert results[0].title == "Python Programming Help"


class TestAsyncSessionHandling:
    """Test async session handling patterns."""
    
    @pytest_asyncio.async_test
    async def test_eager_loading_prevents_lazy_loading(self, async_session):
        """Test that eager loading with selectinload prevents lazy loading issues."""
        # Arrange
        repo = SqlConversationRepository(async_session)
        
        # Create conversation with messages
        conv = DomainConversation(
            id=str(uuid4()),
            user_id=1,
            title="Test Conversation",
            status="active",
            model_name="test-model",
            system_prompt=None,
            data={},
            messages=[],
            total_tokens=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        created_conv = await repo.create(conv)
        
        # Add a message directly to the database
        message = Message(
            id=str(uuid4()),
            conversation_id=created_conv.id,
            role=MessageRole.USER,
            content="Test message",
            raw_content="Test message",
            token_count=10,
            data={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        async_session.add(message)
        await async_session.commit()
        
        # Act - This should work without lazy loading issues
        retrieved = await repo.get(created_conv.id)
        
        # Assert
        assert retrieved is not None
        assert len(retrieved.messages) == 1
        assert retrieved.messages[0].content == "Test message"
        assert retrieved.messages[0].token_count == 10
    
    @pytest_asyncio.async_test
    async def test_repository_handles_session_correctly(self, async_session):
        """Test that repository handles async session without context issues."""
        # Arrange
        repo = SqlConversationRepository(async_session)
        
        # Act - Multiple operations in sequence
        conv1 = DomainConversation(
            id=str(uuid4()),
            user_id=1,
            title="First Conversation",
            status="active",
            model_name="test-model",
            system_prompt=None,
            data={},
            messages=[],
            total_tokens=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        conv2 = DomainConversation(
            id=str(uuid4()),
            user_id=1,
            title="Second Conversation",
            status="active",
            model_name="test-model",
            system_prompt=None,
            data={},
            messages=[],
            total_tokens=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Create both conversations
        created1 = await repo.create(conv1)
        created2 = await repo.create(conv2)
        
        # Retrieve and verify
        retrieved1 = await repo.get(created1.id)
        retrieved2 = await repo.get(created2.id)
        
        # List conversations
        all_conversations = await repo.get_by_user(user_id=1)
        
        # Assert - All operations should work without session context issues
        assert retrieved1.title == "First Conversation"
        assert retrieved2.title == "Second Conversation"
        assert len(all_conversations) == 2


class TestDomainModelConversion:
    """Test conversion between database and domain models."""
    
    @pytest_asyncio.async_test
    async def test_to_domain_conversion_with_messages(self, conversation_repo, async_session):
        """Test that _to_domain correctly converts database models including messages."""
        # Arrange
        conv = DomainConversation(
            id=str(uuid4()),
            user_id=1,
            title="Test Conversation",
            status="active",
            model_name="test-model",
            system_prompt="Test prompt",
            data={"key": "value"},
            messages=[],
            total_tokens=50,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        created_conv = await conversation_repo.create(conv)
        
        # Add messages
        message1 = Message(
            id=str(uuid4()),
            conversation_id=created_conv.id,
            role=MessageRole.USER,
            content="User message",
            raw_content="User message",
            token_count=15,
            data={"source": "user"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        message2 = Message(
            id=str(uuid4()),
            conversation_id=created_conv.id,
            role=MessageRole.ASSISTANT,
            content="Assistant response",
            raw_content="Assistant response",
            token_count=25,
            data={"model": "test"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        async_session.add(message1)
        async_session.add(message2)
        await async_session.commit()
        
        # Act
        retrieved = await conversation_repo.get(created_conv.id)
        
        # Assert
        assert retrieved.id == created_conv.id
        assert retrieved.title == "Test Conversation"
        assert retrieved.status == "active"
        assert retrieved.model_name == "test-model"
        assert retrieved.system_prompt == "Test prompt"
        assert retrieved.data == {"key": "value"}
        assert retrieved.total_tokens == 50
        assert len(retrieved.messages) == 2
        
        # Check message conversion
        user_msg = next(m for m in retrieved.messages if m.role == "user")
        assistant_msg = next(m for m in retrieved.messages if m.role == "assistant")
        
        assert user_msg.content == "User message"
        assert user_msg.token_count == 15
        assert user_msg.data == {"source": "user"}
        
        assert assistant_msg.content == "Assistant response"
        assert assistant_msg.token_count == 25
        assert assistant_msg.data == {"model": "test"}
    
    @pytest_asyncio.async_test
    async def test_enum_status_handling(self, conversation_repo):
        """Test that status field is handled correctly (string vs enum)."""
        # Arrange
        conv = DomainConversation(
            id=str(uuid4()),
            user_id=1,
            title="Status Test",
            status="archived",
            model_name="test-model",
            system_prompt=None,
            data={},
            messages=[],
            total_tokens=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Act
        created = await conversation_repo.create(conv)
        retrieved = await conversation_repo.get(created.id)
        
        # Assert
        assert created.status == "archived"
        assert retrieved.status == "archived"
        # Should be string, not enum object
        assert isinstance(retrieved.status, str)


class TestErrorHandling:
    """Test error handling in repository operations."""
    
    @pytest_asyncio.async_test
    async def test_create_conversation_with_invalid_user(self, conversation_repo):
        """Test creating conversation with non-existent user."""
        # Arrange
        conv = DomainConversation(
            id=str(uuid4()),
            user_id=999,  # Non-existent user
            title="Invalid User Conversation",
            status="active",
            model_name="test-model",
            system_prompt=None,
            data={},
            messages=[],
            total_tokens=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Act & Assert
        with pytest.raises(Exception, match="Failed to create conversation"):
            await conversation_repo.create(conv)
    
    @pytest_asyncio.async_test
    async def test_create_conversation_with_duplicate_id(self, conversation_repo, sample_conversation):
        """Test creating conversation with duplicate ID."""
        # Arrange
        await conversation_repo.create(sample_conversation)
        
        # Create another conversation with same ID
        duplicate_conv = DomainConversation(
            id=sample_conversation.id,  # Same ID
            user_id=1,
            title="Duplicate ID Conversation",
            status="active",
            model_name="test-model",
            system_prompt=None,
            data={},
            messages=[],
            total_tokens=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Act & Assert
        with pytest.raises(Exception, match="Failed to create conversation"):
            await conversation_repo.create(duplicate_conv)