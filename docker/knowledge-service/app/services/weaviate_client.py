"""
Weaviate Vector Database Service
Clean interface for document storage and similarity search
"""

import weaviate
import logging
from typing import List, Dict, Any, Optional
import os
from datetime import datetime
import json
import time

logger = logging.getLogger(__name__)

class WeaviateService:
    """Vector database service for document chunks and embeddings"""
    
    def __init__(self):
        self.client = None
        self.collection_name = "PrivateGPTDocuments"
        
    async def initialize(self):
        """Connect to Weaviate with retry logic"""
        max_retries = 3
        retry_delay = 2
        weaviate_url = os.getenv("WEAVIATE_URL", "http://weaviate-db:8080")
        
        for attempt in range(max_retries):
            try:
                # Create connection with reasonable timeouts
                self.client = weaviate.Client(
                    url=weaviate_url,
                    timeout_config=(10, 30)  # connection, read timeouts
                )
                
                # Test connection
                if self.client.is_ready():
                    logger.info(f"Connected to Weaviate at {weaviate_url}")
                    await self._setup_schema()
                    return
                else:
                    raise Exception("Weaviate not ready")
                    
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to connect after {max_retries} attempts")
                    raise
    
    async def _setup_schema(self):
        """Create document schema if it doesn't exist"""
        try:
            # Check existing classes
            existing_classes = self.client.schema.get()["classes"]
            class_names = [cls["class"] for cls in existing_classes]
            
            if self.collection_name in class_names:
                logger.info(f"Schema for {self.collection_name} exists")
                return
            
            # Create new schema
            schema = {
                "class": self.collection_name,
                "description": "PrivateGPT document chunks for RAG",
                "vectorizer": "none",  # We provide our own vectors
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Chunk text content"
                    },
                    {
                        "name": "documentId", 
                        "dataType": ["string"],
                        "description": "Parent document ID"
                    },
                    {
                        "name": "filename",
                        "dataType": ["string"], 
                        "description": "Original filename"
                    },
                    {
                        "name": "chunkIndex",
                        "dataType": ["int"],
                        "description": "Chunk position in document"
                    },
                    {
                        "name": "contentType",
                        "dataType": ["string"],
                        "description": "Original file MIME type"
                    },
                    {
                        "name": "createdAt",
                        "dataType": ["date"],
                        "description": "Upload timestamp"
                    },
                    {
                        "name": "metadata",
                        "dataType": ["text"],
                        "description": "Additional metadata as JSON"
                    }
                ]
            }
            
            self.client.schema.create_class(schema)
            logger.info(f"Created Weaviate schema: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Schema setup failed: {e}")
            raise
    
    async def store_document_chunks(self, document_id: str, chunks: List[Dict[str, Any]], 
                                   embeddings: List[List[float]]) -> List[str]:
        """Store document chunks with their vector embeddings"""
        try:
            chunk_ids = []
            
            # Use batch processing for efficiency
            with self.client.batch as batch:
                batch.batch_size = 100
                
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    # Prepare document object
                    data_object = {
                        "content": chunk["content"],
                        "documentId": document_id,
                        "filename": chunk.get("filename", ""),
                        "chunkIndex": i,
                        "contentType": chunk.get("content_type", "text/plain"),
                        "createdAt": datetime.utcnow().isoformat() + "Z",
                        "metadata": json.dumps(chunk.get("metadata", {}))
                    }
                    
                    # Add to batch with vector
                    result = batch.add_data_object(
                        data_object=data_object,
                        class_name=self.collection_name,
                        vector=embedding
                    )
                    
                    chunk_ids.append(result)
            
            logger.info(f"Stored {len(chunks)} chunks for document {document_id}")
            return chunk_ids
            
        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            raise
    
    async def search_similar(self, query_embedding: List[float], limit: int = 10, 
                           threshold: float = 0.7, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Find similar document chunks using vector search"""
        try:
            # Build vector similarity query
            query_builder = (
                self.client.query
                .get(self.collection_name, 
                     ["content", "documentId", "filename", "chunkIndex", "metadata"])
                .with_near_vector({"vector": query_embedding})
                .with_limit(limit)
                .with_additional(["certainty", "id"])
            )
            
            # Apply filters if provided
            if filters:
                where_filter = self._build_filter(filters)
                if where_filter:
                    query_builder = query_builder.with_where(where_filter)
            
            # Execute search
            result = query_builder.do()
            documents = result["data"]["Get"][self.collection_name]
            
            # Process results above threshold
            processed_results = []
            for doc in documents:
                certainty = doc["_additional"]["certainty"]
                if certainty >= threshold:
                    processed_results.append({
                        "content": doc["content"],
                        "document_id": doc["documentId"],
                        "chunk_id": doc["_additional"]["id"],
                        "filename": doc.get("filename", ""),
                        "chunk_index": doc.get("chunkIndex", 0),
                        "score": certainty,
                        "metadata": json.loads(doc.get("metadata", "{}"))
                    })
            
            logger.info(f"Found {len(processed_results)} similar chunks")
            return processed_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def _build_filter(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert filter dict to Weaviate where clause"""
        # Simple document ID filtering for now
        # TODO: Expand for complex legal metadata filtering
        if "document_id" in filters:
            return {
                "path": ["documentId"],
                "operator": "Equal",
                "valueString": filters["document_id"]
            }
        return None
    
    async def delete_document(self, document_id: str) -> int:
        """Delete all chunks for a document"""
        try:
            # Build deletion filter
            where_filter = {
                "path": ["documentId"],
                "operator": "Equal",
                "valueString": document_id
            }
            
            # Execute batch deletion
            result = self.client.batch.delete_objects(
                class_name=self.collection_name,
                where=where_filter
            )
            
            deleted_count = result.get("successful", 0)
            logger.info(f"Deleted {deleted_count} chunks for document {document_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise
    
    async def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document metadata from first chunk"""
        try:
            # Query for any chunk of this document
            result = (
                self.client.query
                .get(self.collection_name, 
                     ["documentId", "filename", "contentType", "createdAt", "metadata"])
                .with_where({
                    "path": ["documentId"],
                    "operator": "Equal",
                    "valueString": document_id
                })
                .with_limit(1)
                .do()
            )
            
            documents = result["data"]["Get"][self.collection_name]
            if documents:
                doc = documents[0]
                return {
                    "id": document_id,
                    "filename": doc.get("filename", ""),
                    "content_type": doc.get("contentType", ""),
                    "created_at": doc.get("createdAt", ""),
                    "metadata": json.loads(doc.get("metadata", "{}"))
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document info: {e}")
            return None
    
    async def list_documents(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List all documents with pagination"""
        try:
            # Get sample of chunks to find unique documents
            # More efficient than aggregation on large datasets
            result = (
                self.client.query
                .get(self.collection_name, 
                     ["documentId", "filename", "contentType", "createdAt", "metadata"])
                .with_limit(1000)  # Large enough to catch all documents
                .do()
            )
            
            chunks = result["data"]["Get"][self.collection_name]
            
            # Group by document ID to deduplicate
            document_map = {}
            chunk_counts = {}
            
            for chunk in chunks:
                doc_id = chunk["documentId"]
                if doc_id not in document_map:
                    document_map[doc_id] = {
                        "id": doc_id,
                        "filename": chunk.get("filename", ""),
                        "content_type": chunk.get("contentType", ""),
                        "created_at": chunk.get("createdAt", ""),
                        "metadata": json.loads(chunk.get("metadata", "{}"))
                    }
                    chunk_counts[doc_id] = 0
                chunk_counts[doc_id] += 1
            
            # Add chunk counts to documents
            for doc_id in document_map:
                document_map[doc_id]["chunk_count"] = chunk_counts[doc_id]
            
            # Sort by creation time (newest first)
            documents = list(document_map.values())
            documents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            # Apply pagination
            total = len(documents)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_documents = documents[start_idx:end_idx]
            
            return {
                "documents": paginated_documents,
                "total": total,
                "page": page,
                "page_size": page_size
            }
            
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise
    
    async def close(self):
        """Clean up connection"""
        if self.client:
            # Weaviate client doesn't require explicit closing
            logger.info("Weaviate connection closed")
            self.client = None 