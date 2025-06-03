"""
Weaviate client service for vector database operations
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
    """Service for interacting with Weaviate vector database"""
    
    def __init__(self):
        self.client = None
        self.collection_name = "PrivateGPTDocuments"
        
    async def initialize(self):
        """Initialize connection to Weaviate with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Get Weaviate connection details from environment
                weaviate_url = os.getenv("WEAVIATE_URL", "http://weaviate-db:8080")
                
                self.client = weaviate.Client(
                    url=weaviate_url,
                    timeout_config=(10, 30)  # Increased timeouts: (connection, read)
                )
                
                # Test connection
                if self.client.is_ready():
                    logger.info(f"✅ Connected to Weaviate at {weaviate_url}")
                    await self._ensure_schema()
                    return  # Success, exit retry loop
                else:
                    raise Exception("Weaviate is not ready")
                    
            except Exception as e:
                logger.warning(f"⚠️ Weaviate connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"❌ Failed to connect to Weaviate after {max_retries} attempts")
                    raise
    
    async def _ensure_schema(self):
        """Ensure the document schema exists in Weaviate"""
        try:
            # Check if class already exists
            existing_classes = self.client.schema.get()["classes"]
            class_names = [cls["class"] for cls in existing_classes]
            
            if self.collection_name not in class_names:
                # Create the schema
                schema = {
                    "class": self.collection_name,
                    "description": "PrivateGPT document chunks for RAG",
                    "vectorizer": "none",  # We'll provide our own vectors
                    "properties": [
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "The document chunk content"
                        },
                        {
                            "name": "documentId",
                            "dataType": ["string"],
                            "description": "ID of the parent document"
                        },
                        {
                            "name": "filename",
                            "dataType": ["string"],
                            "description": "Original filename"
                        },
                        {
                            "name": "chunkIndex",
                            "dataType": ["int"],
                            "description": "Index of this chunk within the document"
                        },
                        {
                            "name": "contentType",
                            "dataType": ["string"],
                            "description": "MIME type of the original document"
                        },
                        {
                            "name": "createdAt",
                            "dataType": ["date"],
                            "description": "When the document was uploaded"
                        },
                        {
                            "name": "metadata",
                            "dataType": ["text"],
                            "description": "Additional metadata as JSON string"
                        }
                    ]
                }
                
                self.client.schema.create_class(schema)
                logger.info(f"✅ Created Weaviate schema for {self.collection_name}")
            else:
                logger.info(f"✅ Schema for {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"❌ Failed to ensure schema: {e}")
            raise
    
    async def store_document_chunks(self, document_id: str, chunks: List[Dict[str, Any]], 
                                   embeddings: List[List[float]]) -> List[str]:
        """Store document chunks with their embeddings"""
        try:
            chunk_ids = []
            
            with self.client.batch as batch:
                batch.batch_size = 100
                
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    # Prepare the object
                    data_object = {
                        "content": chunk["content"],
                        "documentId": document_id,
                        "filename": chunk.get("filename", ""),
                        "chunkIndex": i,
                        "contentType": chunk.get("content_type", "text/plain"),
                        "createdAt": datetime.utcnow().isoformat() + "Z",
                        "metadata": json.dumps(chunk.get("metadata", {}))
                    }
                    
                    # Add to batch
                    result = batch.add_data_object(
                        data_object=data_object,
                        class_name=self.collection_name,
                        vector=embedding
                    )
                    
                    chunk_ids.append(result)
            
            logger.info(f"✅ Stored {len(chunks)} chunks for document {document_id}")
            return chunk_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to store chunks: {e}")
            raise
    
    async def search_similar(self, query_embedding: List[float], limit: int = 10, 
                           threshold: float = 0.7, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        try:
            # Build the query
            query_builder = (
                self.client.query
                .get(self.collection_name, ["content", "documentId", "filename", "chunkIndex", "metadata"])
                .with_near_vector({"vector": query_embedding})
                .with_limit(limit)
                .with_additional(["certainty", "id"])
            )
            
            # Add filters if provided
            if filters:
                where_filter = self._build_where_filter(filters)
                if where_filter:
                    query_builder = query_builder.with_where(where_filter)
            
            # Execute query
            result = query_builder.do()
            
            # Process results
            documents = result["data"]["Get"][self.collection_name]
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
            
            logger.info(f"✅ Found {len(processed_results)} similar chunks")
            return processed_results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            raise
    
    def _build_where_filter(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build Weaviate where filter from filters dict"""
        # TODO: Implement comprehensive filter building
        # For now, support basic document ID filtering
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
            # Build delete query
            where_filter = {
                "path": ["documentId"],
                "operator": "Equal", 
                "valueString": document_id
            }
            
            # Execute deletion
            result = self.client.batch.delete_objects(
                class_name=self.collection_name,
                where=where_filter
            )
            
            deleted_count = result.get("successful", 0)
            logger.info(f"✅ Deleted {deleted_count} chunks for document {document_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to delete document: {e}")
            raise
    
    async def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a document"""
        try:
            # Query for document chunks
            result = (
                self.client.query
                .get(self.collection_name, ["documentId", "filename", "contentType", "createdAt", "metadata"])
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
            logger.error(f"❌ Failed to get document info: {e}")
            return None
    
    async def list_documents(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List all documents with pagination - optimized version"""
        try:
            # Get a large sample of chunks to find unique documents
            # This is much faster than aggregation on large datasets
            result = (
                self.client.query
                .get(self.collection_name, ["documentId", "filename", "contentType", "createdAt", "metadata"])
                .with_limit(1000)  # Get enough to find all unique documents
                .do()
            )
            
            chunks = result["data"]["Get"][self.collection_name]
            
            # Group by document ID to get unique documents
            document_map = {}
            document_chunk_counts = {}
            
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
                    document_chunk_counts[doc_id] = 0
                document_chunk_counts[doc_id] += 1
            
            # Add chunk counts
            for doc_id in document_map:
                document_map[doc_id]["chunk_count"] = document_chunk_counts[doc_id]
            
            # Convert to list and sort by creation time (newest first)
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
            logger.error(f"❌ Failed to list documents: {e}")
            raise
    
    async def close(self):
        """Close the Weaviate connection"""
        if self.client:
            # Weaviate client doesn't need explicit closing
            logger.info("✅ Weaviate connection closed")
            self.client = None 