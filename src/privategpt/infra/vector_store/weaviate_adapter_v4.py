from __future__ import annotations

import os
import asyncio
import json
from typing import Sequence, List, Tuple, Dict
import logging

import weaviate
from weaviate import WeaviateClient
import weaviate.classes as wvc

from privategpt.core.ports.vector_store import VectorStorePort

logger = logging.getLogger(__name__)

_COLLECTION = "PrivateGPTChunks"


class WeaviateAdapter(VectorStorePort):
    """Weaviate implementation of VectorStorePort using v4 client."""

    def __init__(self, url: str | None = None):
        self.url = url or os.getenv("WEAVIATE_URL", "http://weaviate:8080")
        self._client: WeaviateClient | None = None

    async def _ensure_client(self) -> WeaviateClient:
        if self._client is not None:
            return self._client

        def _connect() -> WeaviateClient:
            # Extract host and port from URL
            url_parts = self.url.replace("http://", "").replace("https://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 8080
            
            return weaviate.connect_to_local(
                host=host,
                port=port,
                grpc_port=50051,  # Default gRPC port
                skip_init_checks=False
            )

        self._client = await asyncio.to_thread(_connect)
        # ensure ready
        if not await asyncio.to_thread(self._client.is_ready):
            raise RuntimeError("Weaviate not ready at " + self.url)
        await self._ensure_schema()
        return self._client

    async def _ensure_schema(self) -> None:
        client = self._client
        assert client is not None
        
        def _create_schema():
            # Check if collection exists
            try:
                collection = client.collections.get(_COLLECTION)
                logger.info(f"Collection {_COLLECTION} already exists")
            except Exception:
                # Create collection if it doesn't exist
                client.collections.create(
                    name=_COLLECTION,
                    description="RAG document chunks",
                    vectorizer_config=wvc.config.Configure.Vectorizer.none(),
                    properties=[
                        wvc.config.Property(
                            name="text",
                            data_type=wvc.config.DataType.TEXT
                        ),
                        wvc.config.Property(
                            name="metadata",
                            data_type=wvc.config.DataType.TEXT
                        ),
                    ]
                )
                logger.info(f"Created collection {_COLLECTION}")
        
        await asyncio.to_thread(_create_schema)

    # Port implementation -----------------------------------------
    async def add_vectors(self, embeddings: List[Sequence[float]], metadatas: List[dict], ids: List[str]) -> None:
        client = await self._ensure_client()

        def _batch():
            collection = client.collections.get(_COLLECTION)
            with collection.batch.dynamic() as batch:
                for vector, meta, _id in zip(embeddings, metadatas, ids):
                    batch.add_object(
                        properties={
                            "text": meta.get("text", ""),
                            "metadata": json.dumps({
                                "document_id": meta.get("document_id"),
                                "position": meta.get("position"),
                                **meta.get("metadata", {})
                            })
                        },
                        vector=list(vector),
                        uuid=_id
                    )
        
        await asyncio.to_thread(_batch)

    async def similarity_search(
        self,
        embedding: Sequence[float],
        top_k: int = 5,
        filters: Dict | None = None,
    ) -> List[Tuple[str, float]]:
        client = await self._ensure_client()

        def _query():
            collection = client.collections.get(_COLLECTION)
            response = collection.query.near_vector(
                near_vector=list(embedding),
                limit=top_k,
                return_metadata=["certainty"],
                return_properties=["text", "metadata"]
            )
            
            results = []
            for obj in response.objects:
                # Get UUID as string
                obj_id = str(obj.uuid)
                # Get certainty score
                certainty = obj.metadata.certainty if obj.metadata.certainty else 0.0
                # Include metadata in result
                metadata = {}
                if obj.properties.get("metadata"):
                    try:
                        metadata = json.loads(obj.properties["metadata"])
                    except:
                        pass
                results.append((obj_id, certainty, metadata))
            
            return results

        return await asyncio.to_thread(_query)
    
    async def close(self):
        """Close the Weaviate client connection."""
        if self._client:
            await asyncio.to_thread(self._client.close)
            self._client = None 