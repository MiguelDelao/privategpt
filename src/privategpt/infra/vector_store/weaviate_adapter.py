from __future__ import annotations

import os
import asyncio
from typing import Sequence, List, Tuple, Dict
import logging

import weaviate

from privategpt.core.ports.vector_store import VectorStorePort

logger = logging.getLogger(__name__)

_COLLECTION = "PrivateGPTChunks"


class WeaviateAdapter(VectorStorePort):
    """Weaviate implementation of VectorStorePort (sync client wrapped with asyncio.to_thread)."""

    def __init__(self, url: str | None = None):
        self.url = url or os.getenv("WEAVIATE_URL", "http://weaviate-db:8080")
        self._client: weaviate.Client | None = None

    async def _ensure_client(self) -> weaviate.Client:
        if self._client is not None:
            return self._client

        def _connect() -> weaviate.Client:
            return weaviate.Client(url=self.url, timeout_config=(5, 30))

        self._client = await asyncio.to_thread(_connect)
        # ensure ready
        if not await asyncio.to_thread(self._client.is_ready):
            raise RuntimeError("Weaviate not ready at " + self.url)
        await self._ensure_schema()
        return self._client

    async def _ensure_schema(self) -> None:
        client = self._client
        assert client is not None
        classes = await asyncio.to_thread(lambda: client.schema.get()["classes"])
        if any(cls["class"] == _COLLECTION for cls in classes):
            return
        schema = {
            "class": _COLLECTION,
            "description": "RAG document chunks",
            "vectorizer": "none",
            "properties": [
                {"name": "text", "dataType": ["text"]},
                {"name": "metadata", "dataType": ["text"]},
            ],
        }
        await asyncio.to_thread(client.schema.create_class, schema)

    # Port implementation -----------------------------------------
    async def add_vectors(self, embeddings: List[Sequence[float]], metadatas: List[dict], ids: List[str]) -> None:
        client = await self._ensure_client()

        def _batch():
            with client.batch as batch:
                batch.batch_size = 100
                for vector, meta, _id in zip(embeddings, metadatas, ids):
                    data_obj = {"text": meta.get("text", ""), "metadata": meta.get("metadata", "")}
                    batch.add_data_object(data_obj, class_name=_COLLECTION, vector=vector, uuid=_id)
        await asyncio.to_thread(_batch)

    async def similarity_search(
        self,
        embedding: Sequence[float],
        top_k: int = 5,
        filters: Dict | None = None,
    ) -> List[Tuple[str, float]]:
        client = await self._ensure_client()

        def _query():
            q = (
                client.query
                .get(_COLLECTION, ["text"])
                .with_near_vector({"vector": embedding})
                .with_limit(top_k)
                .with_additional(["certainty", "id"])
            )
            res = q.do()
            objs = res["data"]["Get"][_COLLECTION]
            return [(o["_additional"]["id"], o["_additional"]["certainty"]) for o in objs]

        return await asyncio.to_thread(_query) 