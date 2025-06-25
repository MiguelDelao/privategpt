"""Compatibility layer for Weaviate client v3 API."""
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
    """Weaviate implementation with v3 compatibility."""

    def __init__(self, url: str | None = None):
        self.url = url or os.getenv("WEAVIATE_URL", "http://weaviate:8080")
        self._client = None

    async def _ensure_client(self):
        if self._client is not None:
            return self._client

        def _connect():
            # Extract host from URL
            url_parts = self.url.replace("http://", "").replace("https://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 8080
            
            logger.info(f"Connecting to Weaviate at {host}:{port}")
            
            # Use v4 connection method
            return weaviate.connect_to_local(
                host=host,
                port=port,
                grpc_port=50051,
                skip_init_checks=False
            )

        self._client = await asyncio.to_thread(_connect)
        
        # Check if ready
        try:
            is_ready = await asyncio.to_thread(lambda: self._client.is_ready())
            if not is_ready:
                raise RuntimeError(f"Weaviate not ready at {self.url}")
        except Exception as e:
            logger.warning(f"Failed to check readiness: {e}, assuming ready")
        
        await self._ensure_schema()
        return self._client

    async def _ensure_schema(self) -> None:
        client = self._client
        assert client is not None
        
        def _create_schema():
            try:
                # Check if collection exists
                collections = client.collections.list_all()
                if _COLLECTION in collections:
                    logger.info(f"Collection {_COLLECTION} already exists")
                    return
                
                # Create collection with v4 API
                from weaviate.classes.config import Configure, Property, DataType
                
                client.collections.create(
                    name=_COLLECTION,
                    description="RAG document chunks",
                    vectorizer_config=Configure.Vectorizer.none(),
                    properties=[
                        Property(name="text", data_type=DataType.TEXT),
                        Property(name="metadata", data_type=DataType.TEXT),
                    ]
                )
                logger.info(f"Created collection {_COLLECTION}")
            except Exception as e:
                logger.error(f"Failed to create schema: {e}")
                # Continue anyway - may already exist
        
        await asyncio.to_thread(_create_schema)

    async def add_vectors(self, embeddings: List[Sequence[float]], metadatas: List[dict], ids: List[str]) -> None:
        client = await self._ensure_client()

        def _batch():
            try:
                # Get collection
                collection = client.collections.get(_COLLECTION)
                
                # Add objects in batch with v4 API
                with collection.batch.dynamic() as batch:
                    for vector, meta, _id in zip(embeddings, metadatas, ids):
                        batch.add_object(
                            properties={
                                "text": meta.get("text", ""), 
                                "metadata": str(meta.get("metadata", ""))
                            },
                            vector=list(vector),
                            uuid=_id
                        )
            except Exception as e:
                logger.error(f"Batch insert failed: {e}")
                raise
        
        await asyncio.to_thread(_batch)

    async def similarity_search(
        self,
        embedding: Sequence[float],
        top_k: int = 5,
        filters: Dict | None = None,
    ) -> List[Tuple[str, float]]:
        client = await self._ensure_client()

        def _query():
            try:
                # Get collection
                collection = client.collections.get(_COLLECTION)
                
                # Query with v4 API
                response = collection.query.near_vector(
                    near_vector=list(embedding),
                    limit=top_k,
                    return_metadata=["certainty"]
                )
                
                results = []
                for obj in response.objects:
                    # Get UUID as string
                    obj_id = str(obj.uuid)
                    # Get certainty score
                    certainty = obj.metadata.certainty if hasattr(obj.metadata, 'certainty') else 0.0
                    results.append((obj_id, certainty))
                
                return results
            except Exception as e:
                logger.error(f"Query failed: {e}")
                return []

        return await asyncio.to_thread(_query)