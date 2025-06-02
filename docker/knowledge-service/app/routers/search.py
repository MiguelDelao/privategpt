"""
Search router for vector similarity search
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
import logging
import time

from ..models.schemas import SearchRequest, SearchResponse, SearchResult
from ..services.weaviate_client import WeaviateService
from ..services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter()

# Service instance
embedding_service = EmbeddingService()


async def get_weaviate_service() -> WeaviateService:
    """Dependency to get Weaviate service from app state"""
    from fastapi import Request
    request = Request.scope
    if hasattr(request.app.state, 'weaviate'):
        return request.app.state.weaviate
    raise HTTPException(status_code=503, detail="Weaviate service not available")


@router.post("/", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    Search for similar document chunks using vector similarity
    
    Uses the query text to find semantically similar content in the vector database.
    """
    start_time = time.time()
    
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        logger.info(f"🔍 Searching for: '{request.query[:100]}...' (limit={request.limit})")
        
        # Initialize embedding service if needed
        if not embedding_service.model:
            await embedding_service.initialize()
        
        # Generate embedding for the query
        query_embedding = await embedding_service.embed_text(request.query)
        
        # Search in Weaviate
        results = await weaviate.search_similar(
            query_embedding=query_embedding,
            limit=request.limit,
            threshold=request.threshold,
            filters=request.filters
        )
        
        # Convert to response format
        search_results = []
        for result in results:
            search_result = SearchResult(
                content=result["content"],
                metadata=result["metadata"],
                score=result["score"],
                document_id=result["document_id"],
                chunk_id=result["chunk_id"]
            )
            search_results.append(search_result)
        
        # Prepare response
        took_ms = int((time.time() - start_time) * 1000)
        response = SearchResponse(
            results=search_results,
            query=request.query,
            total_results=len(search_results),
            took_ms=took_ms
        )
        
        logger.info(f"✅ Search completed in {took_ms}ms: {len(search_results)} results")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/similar/{document_id}")
async def find_similar_documents(
    document_id: str,
    limit: int = 10,
    threshold: float = 0.7,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    Find documents similar to a specific document
    
    Uses the first chunk of the document as the query vector.
    """
    try:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        logger.info(f"🔍 Finding documents similar to: {document_id}")
        
        # Get the first chunk of the document to use as query
        # Use a dummy embedding to search for this document's chunks
        dummy_embedding = [0.0] * 384  # BGE-small embedding dimension
        
        document_chunks = await weaviate.search_similar(
            query_embedding=dummy_embedding,
            limit=1,
            threshold=0.0,
            filters={"document_id": document_id}
        )
        
        if not document_chunks:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Use the first chunk's content as query
        query_text = document_chunks[0]["content"]
        
        # Initialize embedding service if needed
        if not embedding_service.model:
            await embedding_service.initialize()
        
        # Generate embedding for the query
        query_embedding = await embedding_service.embed_text(query_text)
        
        # Search for similar chunks, excluding the original document
        all_results = await weaviate.search_similar(
            query_embedding=query_embedding,
            limit=limit * 2,  # Get more to filter out same document
            threshold=threshold,
            filters={}
        )
        
        # Filter out chunks from the same document
        filtered_results = []
        seen_documents = set()
        
        for result in all_results:
            if result["document_id"] != document_id:
                if result["document_id"] not in seen_documents:
                    filtered_results.append(result)
                    seen_documents.add(result["document_id"])
                    
                    if len(filtered_results) >= limit:
                        break
        
        # Convert to search results
        search_results = []
        for result in filtered_results:
            search_result = SearchResult(
                content=result["content"],
                metadata=result["metadata"],
                score=result["score"],
                document_id=result["document_id"],
                chunk_id=result["chunk_id"]
            )
            search_results.append(search_result)
        
        logger.info(f"✅ Found {len(search_results)} similar documents")
        
        return {
            "query_document_id": document_id,
            "similar_documents": search_results,
            "total_found": len(search_results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Similar document search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Similar search failed: {str(e)}")


@router.post("/semantic")
async def semantic_search(
    query: str,
    document_ids: Optional[List[str]] = None,
    limit: int = 10,
    threshold: float = 0.7,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    Advanced semantic search with optional document filtering
    
    Allows searching within specific documents or across all documents.
    """
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        logger.info(f"🔍 Semantic search: '{query[:50]}...' in {len(document_ids) if document_ids else 'all'} documents")
        
        # Initialize embedding service if needed
        if not embedding_service.model:
            await embedding_service.initialize()
        
        # Generate embedding for the query
        query_embedding = await embedding_service.embed_text(query)
        
        # Build filters
        filters = {}
        if document_ids:
            # For simplicity, search in first document (could be enhanced for multiple)
            if len(document_ids) == 1:
                filters["document_id"] = document_ids[0]
            # TODO: Support multiple document IDs in filters
        
        # Search in Weaviate
        results = await weaviate.search_similar(
            query_embedding=query_embedding,
            limit=limit,
            threshold=threshold,
            filters=filters
        )
        
        # Group results by document for better presentation
        document_groups = {}
        for result in results:
            doc_id = result["document_id"]
            if doc_id not in document_groups:
                document_groups[doc_id] = {
                    "document_id": doc_id,
                    "filename": result["metadata"].get("filename", "Unknown"),
                    "chunks": [],
                    "best_score": 0.0
                }
            
            document_groups[doc_id]["chunks"].append(result)
            document_groups[doc_id]["best_score"] = max(
                document_groups[doc_id]["best_score"],
                result["score"]
            )
        
        # Sort by best score
        sorted_documents = sorted(
            document_groups.values(),
            key=lambda x: x["best_score"],
            reverse=True
        )
        
        return {
            "query": query,
            "document_results": sorted_documents,
            "total_documents": len(sorted_documents),
            "total_chunks": len(results),
            "filters_applied": filters
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")


@router.get("/suggestions")
async def get_search_suggestions(
    query: str,
    limit: int = 5,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    Get search suggestions based on partial query
    
    Returns potential search terms based on document content.
    """
    try:
        if len(query.strip()) < 2:
            return {"suggestions": []}
        
        # For a simple implementation, just return similar chunks
        # In a real system, you might have a dedicated suggestions index
        
        # Initialize embedding service if needed
        if not embedding_service.model:
            await embedding_service.initialize()
        
        # Generate embedding for partial query
        query_embedding = await embedding_service.embed_text(query)
        
        # Search for similar content
        results = await weaviate.search_similar(
            query_embedding=query_embedding,
            limit=limit,
            threshold=0.5,
            filters={}
        )
        
        # Extract key phrases from results
        suggestions = []
        for result in results:
            content = result["content"]
            # Simple suggestion extraction - get first few words
            words = content.split()[:10]
            suggestion = " ".join(words)
            if suggestion and suggestion not in suggestions:
                suggestions.append(suggestion)
        
        return {
            "query": query,
            "suggestions": suggestions[:limit]
        }
        
    except Exception as e:
        logger.error(f"❌ Suggestions failed: {e}")
        return {"suggestions": []} 