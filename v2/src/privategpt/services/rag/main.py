from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uuid
from datetime import datetime

from privategpt.infra.database.async_session import get_async_session, engine
from privategpt.infra.database import models
from privategpt.infra.database.document_repository import SqlDocumentRepository
from privategpt.infra.database.chunk_repository import SqlChunkRepository
from privategpt.infra.splitters.simple import SimpleSplitterAdapter
from privategpt.infra.vector_store.memory import InMemoryVectorStore
from privategpt.core.domain.document import Document
from privategpt.infra.chat.echo import EchoChatAdapter
from privategpt.services.rag.service import RagService
from privategpt.core.domain.query import SearchQuery
from privategpt.infra.vector_store.weaviate_adapter import WeaviateAdapter  # noqa: E501
from privategpt.infra.embedder.bge_adapter import BgeEmbedderAdapter
from privategpt.infra.embedder.fake import FakeEmbedderAdapter

# create tables at startup (sync call inside async lifespan is okay for sqlite)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create tables
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    # singletons choose real vs fake
    use_fake = os.getenv("USE_FAKE_ADAPTERS", "true").lower() == "true"

    app.state.splitter = SimpleSplitterAdapter()
    if use_fake:
        app.state.embedder = FakeEmbedderAdapter()
        app.state.vector_store = InMemoryVectorStore()
    else:
        app.state.embedder = BgeEmbedderAdapter()
        app.state.vector_store = WeaviateAdapter()

    yield

    # nothing to cleanup yet


def get_splitter(request: Request):
    return request.app.state.splitter

def get_embedder(request: Request):
    return request.app.state.embedder

def get_vector_store(request: Request):
    return request.app.state.vector_store


app = FastAPI(
    title="PrivateGPT RAG Service",
    description="Retrieval-Augmented Generation micro-service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    session=Depends(get_async_session),
    splitter=Depends(get_splitter),
    embedder=Depends(get_embedder),
    store=Depends(get_vector_store),
):
    content = await file.read()
    text = content.decode(errors="ignore")
    parts = splitter.split(text)

    doc = Document(
        id=None,
        title=file.filename,
        file_path="uploaded",
        uploaded_at=datetime.utcnow(),
    )
    repo = SqlDocumentRepository(session)
    doc = await repo.add(doc)

    embeddings = await embedder.embed_documents(parts)
    ids = [f"{doc.id}_{i}" for i, _ in enumerate(parts)]
    await store.add_vectors(embeddings, [{} for _ in parts], ids)

    return {"id": doc.id, "chunks": len(parts)}


def get_rag_service(request: Request, session=Depends(get_async_session)):
    chunk_repo = SqlChunkRepository(session)
    return RagService(
        repo=SqlDocumentRepository(session),
        splitter=request.app.state.splitter,
        embedder=request.app.state.embedder,
        vector_store=request.app.state.vector_store,
        chunk_repo=chunk_repo,
        chat_llm=EchoChatAdapter(),
    )


@app.post("/search")
async def search(query: SearchQuery, svc=Depends(get_rag_service)):
    return await svc.search(query)


@app.post("/chat")
async def chat(body: dict, svc=Depends(get_rag_service)):
    question = body.get("question")
    if not question:
        raise HTTPException(status_code=422, detail="question required")
    return await svc.chat(question) 