"""
Async Document Processing Tasks
Real-time progress tracking with Redis storage
"""

import json
import time
import redis
from typing import Dict, Any, List
from datetime import datetime
import asyncio

from ..celery_app import celery_app
from ..services.chunking import ChunkingService
from ..services.embedding import EmbeddingService
from ..services.weaviate_client import WeaviateService

# Redis client for progress tracking
redis_client = redis.Redis.from_url(
    celery_app.conf.broker_url.replace('/0', '/2')  # Use DB 2 for progress
)

class ProgressTracker:
    """Manages real-time progress updates in Redis"""
    
    @staticmethod
    def update_progress(task_id: str, progress_data: Dict[str, Any]):
        """Update progress in Redis with expiration"""
        key = f"task_progress:{task_id}"
        
        # Add timestamp
        progress_data["updated_at"] = datetime.utcnow().isoformat()
        
        # Store with 1 hour expiration
        redis_client.setex(key, 3600, json.dumps(progress_data))
    
    @staticmethod
    def get_progress(task_id: str) -> Dict[str, Any]:
        """Get current progress from Redis"""
        key = f"task_progress:{task_id}"
        data = redis_client.get(key)
        
        if data:
            return json.loads(data)
        
        return {
            "status": "PENDING",
            "progress": 0.0,
            "stage": "Initializing...",
            "message": "Task not found or expired"
        }

@celery_app.task(bind=True)
def process_document_async(self, file_content_b64: str, content_type: str, 
                          filename: str, metadata: Dict[str, Any] = None):
    """
    Document processing with real-time progress updates
    
    Args:
        file_content_b64: Base64 encoded file content
        content_type: MIME type
        filename: Original filename
        metadata: Additional metadata
    """
    import base64
    import time
    import json
    
    task_id = self.request.id
    tracker = ProgressTracker()
    
    async def _async_process():
        try:
            # Stage 1: Initialize (5%)
            tracker.update_progress(task_id, {
                "status": "PROCESSING",
                "progress": 0.05,
                "stage": "Initializing services...",
                "filename": filename,
                "chunks_processed": 0,
                "chunks_total": 0,
                "total_stages": 5
            })
            
            # Decode file content
            file_content = base64.b64decode(file_content_b64)
            
            # Initialize services
            chunking_service = ChunkingService()
            embedding_service = EmbeddingService()
            weaviate_service = WeaviateService()
            
            # Stage 2: Text Extraction (20%)
            tracker.update_progress(task_id, {
                "status": "PROCESSING", 
                "progress": 0.20,
                "stage": f"Extracting text from {filename}...",
                "filename": filename,
                "chunks_processed": 0,
                "chunks_total": 0  # Will be updated once we know the count
            })
            
            # Extract text and create chunks
            doc_result = await chunking_service.process_document(
                file_content=file_content,
                content_type=content_type,
                filename=filename,
                metadata=metadata
            )
            
            chunk_count = len(doc_result["chunks"])
            
            # Stage 3: Embedding Generation (starts at 20%, progresses to 90% based on chunks)
            tracker.update_progress(task_id, {
                "status": "PROCESSING",
                "progress": 0.20,
                "stage": f"Generating embeddings for {chunk_count} chunks...",
                "filename": filename,
                "chunks_processed": 0,
                "chunks_total": chunk_count
            })
            
            # Initialize embedding service
            await embedding_service.initialize()
            
            # Process embeddings in batches with progress updates
            chunk_texts = [chunk["content"] for chunk in doc_result["chunks"]]
            batch_size = 50
            all_embeddings = []
            
            for i in range(0, len(chunk_texts), batch_size):
                batch_end = min(i + batch_size, len(chunk_texts))
                batch_texts = chunk_texts[i:batch_end]
                
                # Calculate actual progress based on chunks processed
                chunks_processed = i + len(batch_texts)
                # Progress: 20% for setup + (chunks_processed / total_chunks) * 70% + 10% for final storage
                actual_progress = 0.20 + (chunks_processed / chunk_count) * 0.70
                
                tracker.update_progress(task_id, {
                    "status": "PROCESSING",
                    "progress": actual_progress,
                    "stage": f"Processing embeddings batch {i//batch_size + 1}/{(len(chunk_texts) + batch_size - 1)//batch_size}...",
                    "filename": filename,
                    "chunks_processed": chunks_processed,
                    "chunks_total": chunk_count
                })
                
                # Generate embeddings for batch
                batch_embeddings = await embedding_service.embed_texts(batch_texts)
                all_embeddings.extend(batch_embeddings)
                
                # Small delay to allow other tasks to run
                await asyncio.sleep(0.1)
            
            # Stage 4: Vector Storage (90%)
            tracker.update_progress(task_id, {
                "status": "PROCESSING",
                "progress": 0.90,
                "stage": "Storing in vector database...",
                "filename": filename,
                "chunks_processed": chunk_count,
                "chunks_total": chunk_count
            })
            
            # Initialize and store in Weaviate
            await weaviate_service.initialize()
            chunk_ids = await weaviate_service.store_document_chunks(
                document_id=doc_result["document_id"],
                chunks=doc_result["chunks"],
                embeddings=all_embeddings
            )
            
            # Stage 5: Complete (100%)
            result = {
                "id": doc_result["document_id"],  # Use 'id' to match DocumentResponse schema
                "filename": filename,
                "content_type": content_type,
                "size": len(file_content),
                "chunk_count": chunk_count,
                "created_at": datetime.utcnow().isoformat(),
                "metadata": doc_result["metadata"]
            }
            
            tracker.update_progress(task_id, {
                "status": "SUCCESS",
                "progress": 1.0,
                "stage": "Document processing complete!",
                "filename": filename,
                "chunks_processed": chunk_count,
                "chunks_total": chunk_count,
                "result": result
            })
            
            return result
            
        except Exception as e:
            # Error handling with progress update
            tracker.update_progress(task_id, {
                "status": "FAILURE",
                "progress": 0.0,
                "stage": "Processing failed",
                "filename": filename,
                "error": str(e),
                "error_type": type(e).__name__
            })
            
            # Re-raise for Celery's error handling
            raise
    
    # Run the async code in the event loop
    return asyncio.run(_async_process())

@celery_app.task
def cleanup_expired_progress():
    """Cleanup task to remove expired progress entries"""
    # This task can be scheduled to run periodically
    pattern = "task_progress:*"
    
    for key in redis_client.scan_iter(match=pattern):
        ttl = redis_client.ttl(key)
        if ttl < 60:  # Less than 1 minute remaining
            redis_client.delete(key) 