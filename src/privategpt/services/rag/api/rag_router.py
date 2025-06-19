from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.infra.database.async_session import get_async_session
from privategpt.infra.database.document_repository import SqlDocumentRepository
from privategpt.core.domain.document import DocumentStatus, Document
from privategpt.core.domain.query import SearchQuery
from privategpt.infra.tasks.celery_app import app as celery_app  # noqa: E501
from privategpt.infra.tasks.service_factory import build_rag_service
from privategpt.infra.tasks.celery_queue import CeleryTaskQueueAdapter
from celery.result import AsyncResult

router = APIRouter(prefix="/rag", tags=["rag"])


class DocumentIn(BaseModel):
    title: str = Field(...)
    text: str = Field(..., min_length=1)


class DocumentOut(BaseModel):
    id: int
    title: str
    status: DocumentStatus
    error: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)


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


@router.get("/progress/{task_id}")
def task_progress(task_id: str):
    res: AsyncResult = celery_app.AsyncResult(task_id)
    return {"state": res.state, "info": res.info}


@router.post("/chat", response_model=ChatAnswer)
async def rag_chat(req: ChatRequest, session: AsyncSession = Depends(get_async_session)):
    rag = build_rag_service(session)
    ans = await rag.chat(req.question)
    return {"answer": ans.text, "citations": ans.citations} 