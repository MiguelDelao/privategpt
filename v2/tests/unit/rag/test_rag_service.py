import pytest
import pytest_asyncio

from privategpt.services.rag.service import RagService
from privategpt.infra.splitters.simple import SimpleSplitterAdapter
from privategpt.infra.embedder.fake import FakeEmbedderAdapter
from privategpt.infra.vector_store.memory import InMemoryVectorStore
from privategpt.core.domain.query import SearchQuery
from privategpt.infra.database.document_repository import SqlDocumentRepository
from privategpt.infra.database.chunk_repository import SqlChunkRepository
from privategpt.infra.database.async_session import get_async_session, engine
from privategpt.infra.database import models
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(scope="module", autouse=True)
async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    # no teardown


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    async with get_async_session() as s:
        yield s


@pytest.mark.asyncio
async def test_ingest_and_search(session):
    splitter = SimpleSplitterAdapter()
    embedder = FakeEmbedderAdapter()
    store = InMemoryVectorStore()
    repo = SqlDocumentRepository(session)
    chunk_repo = SqlChunkRepository(session)
    svc = RagService(repo, splitter, embedder, store, chunk_repo, chat_llm=None)  # type: ignore[arg-type]

    text = "Para1.\n\nPara2.\n\nPara3."
    doc = await svc.ingest_document("doc.txt", "mem", text)
    assert doc.id is not None

    results = await svc.search(SearchQuery(text="Para2", top_k=2))
    assert len(results) == 2
    assert results[0][1] >= results[1][1] 