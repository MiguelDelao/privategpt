"""Synchronous Celery task implementation to avoid asyncio issues."""
import logging
from typing import List
from celery import current_task
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker

from privategpt.infra.database.models import Document as DocumentModel
from privategpt.core.domain.document import DocumentStatus
from privategpt.infra.splitters.simple import SimpleSplitterAdapter
from privategpt.infra.embedder.bge_adapter import BgeEmbedderAdapter
import asyncio
import json

logger = logging.getLogger(__name__)


def process_document_sync(doc_id: int, file_path: str, title: str, text: str):
    """Synchronous document processing function."""
    
    # Create sync database connection
    engine = create_engine("postgresql://privategpt:secret@db:5432/privategpt")
    Session = sessionmaker(bind=engine)
    
    def update_progress(stage: str, progress: int, message: str):
        """Update task progress in Celery backend."""
        current_task.update_state(
            state='PROGRESS',
            meta={
                'stage': stage,
                'progress': progress,
                'message': message,
                'document_id': doc_id,
                'title': title
            }
        )
    
    with Session() as session:
        try:
            # Get document
            doc = session.query(DocumentModel).filter_by(id=doc_id).first()
            if not doc:
                raise ValueError(f"Document {doc_id} not found")
            
            # Update status to processing
            doc.status = DocumentStatus.PROCESSING.value
            doc.processing_progress = json.dumps({"stage": "starting", "progress": 0})
            session.commit()
            
            update_progress("splitting", 10, "Splitting document into chunks...")
            
            # Split text
            splitter = SimpleSplitterAdapter()
            parts = splitter.split(text)
            num_chunks = len(parts)
            
            update_progress("splitting", 20, f"Split into {num_chunks} chunks")
            
            # Update document progress
            doc.processing_progress = json.dumps({
                "stage": "embedding", 
                "progress": 20,
                "chunks_total": num_chunks
            })
            session.commit()
            
            # Generate embeddings
            update_progress("embedding", 30, f"Generating embeddings for {num_chunks} chunks...")
            
            embedder = BgeEmbedderAdapter()
            
            # Use asyncio.run for the async embed_documents method
            async def get_embeddings():
                batch_size = 10
                all_embeddings = []
                for i in range(0, num_chunks, batch_size):
                    batch = parts[i:i+batch_size]
                    batch_embeddings = await embedder.embed_documents(batch)
                    all_embeddings.extend(batch_embeddings)
                    
                    # Update progress
                    progress = 30 + int((i / num_chunks) * 40)  # 30-70% for embeddings
                    update_progress(
                        "embedding", 
                        progress, 
                        f"Embedded {min(i + batch_size, num_chunks)}/{num_chunks} chunks"
                    )
                return all_embeddings
            
            embeddings = asyncio.run(get_embeddings())
            
            # Store in vector database
            update_progress("storing", 70, "Storing vectors in database...")
            
            # Use asyncio.run for vector store operations
            async def store_vectors():
                from privategpt.infra.vector_store.weaviate_adapter import WeaviateAdapter
                vector_store = WeaviateAdapter()
                
                # Generate proper UUIDs for Weaviate
                import uuid
                ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, f"doc_{doc_id}_chunk_{i}")) for i in range(num_chunks)]
                await vector_store.add_vectors(
                    embeddings,
                    [{"text": p, "document_id": doc_id, "position": i} for i, p in enumerate(parts)],
                    ids,
                )
                
                # Close the client properly
                if hasattr(vector_store, 'close'):
                    await vector_store.close()
            
            asyncio.run(store_vectors())
            
            update_progress("storing", 85, "Saving chunks to database...")
            
            # Save chunks using sync operations
            from privategpt.infra.database.models import Chunk as ChunkModel
            
            for i, (part, emb) in enumerate(zip(parts, embeddings)):
                chunk = ChunkModel(
                    document_id=doc_id,
                    position=i,
                    text=part,
                    embedding=json.dumps(emb)  # Convert to JSON string
                )
                session.add(chunk)
            
            session.commit()
            
            update_progress("finalizing", 95, "Finalizing document processing...")
            
            # Update document status
            doc.status = DocumentStatus.COMPLETE.value
            doc.processing_progress = json.dumps({
                "stage": "complete", 
                "progress": 100,
                "chunks_total": num_chunks,
                "completed_at": "now"
            })
            session.commit()
            
            update_progress("complete", 100, f"Successfully processed {num_chunks} chunks")
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            
            # Update document with error
            doc = session.query(DocumentModel).filter_by(id=doc_id).first()
            if doc:
                doc.status = DocumentStatus.FAILED.value
                doc.error = str(e)
                doc.processing_progress = json.dumps({
                    "stage": "failed",
                    "progress": 0,
                    "error": str(e)
                })
                session.commit()
            
            raise