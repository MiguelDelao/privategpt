"""
Chat router for RAG-powered conversations
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
import logging
import time
import httpx
import os

from ..models.schemas import ChatRequest, ChatResponse, ChatMessage, SearchResult
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


@router.post("/", response_model=ChatResponse)
async def chat_with_documents(
    request: ChatRequest,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    RAG-powered chat endpoint
    
    Retrieves relevant document contexts and generates responses using LLM.
    """
    start_time = time.time()
    
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        # Get the latest user message
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")
        
        latest_query = user_messages[-1].content
        logger.info(f"💬 Processing chat query: '{latest_query[:100]}...'")
        
        # Initialize embedding service if needed
        if not embedding_service.model:
            await embedding_service.initialize()
        
        # Generate embedding for the query
        query_embedding = await embedding_service.embed_text(latest_query)
        
        # Retrieve relevant context from documents
        context_results = await weaviate.search_similar(
            query_embedding=query_embedding,
            limit=request.search_limit,
            threshold=0.6,  # Slightly lower threshold for chat
            filters={}
        )
        
        # Build context from retrieved documents
        context_parts = []
        sources = []
        
        for result in context_results:
            context_parts.append(f"[Source: {result['filename']}]\n{result['content']}")
            
            if request.include_sources:
                search_result = SearchResult(
                    content=result["content"],
                    metadata=result["metadata"],
                    score=result["score"],
                    document_id=result["document_id"],
                    chunk_id=result["chunk_id"]
                )
                sources.append(search_result)
        
        context_text = "\n\n".join(context_parts)
        
        # Build the prompt for the LLM
        system_prompt = """You are a helpful assistant that answers questions based on the provided context documents. 
Use only the information from the context to answer questions. If the context doesn't contain enough information to answer the question, say so clearly.
Be concise but comprehensive in your responses."""
        
        if context_text:
            user_prompt = f"""Context documents:
{context_text}

User question: {latest_query}

Please provide an answer based on the context documents above."""
        else:
            user_prompt = f"""I don't have any relevant context documents for your question: "{latest_query}"

I can only answer questions based on documents that have been uploaded to the system. Could you please upload relevant documents first, or ask a question about documents that are already in the system?"""
        
        # Generate response using Ollama
        llm_response = await _generate_llm_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        # Create response message
        assistant_message = ChatMessage(
            role="assistant",
            content=llm_response
        )
        
        # Prepare final response
        took_ms = int((time.time() - start_time) * 1000)
        response = ChatResponse(
            message=assistant_message,
            sources=sources if request.include_sources else None,
            took_ms=took_ms,
            model_used="ollama"  # Could be made configurable
        )
        
        logger.info(f"✅ Chat response generated in {took_ms}ms with {len(sources)} sources")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/stream")
async def stream_chat_with_documents(
    request: ChatRequest,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    Streaming RAG-powered chat endpoint
    
    Returns streamed response for real-time chat experience.
    """
    # TODO: Implement streaming response
    # For now, redirect to regular chat
    return await chat_with_documents(request, weaviate)


@router.post("/explain")
async def explain_answer(
    query: str,
    response: str,
    weaviate: WeaviateService = Depends(get_weaviate_service)
):
    """
    Explain how an answer was derived from the source documents
    
    Shows which parts of the context were most relevant for the response.
    """
    try:
        # Initialize embedding service if needed
        if not embedding_service.model:
            await embedding_service.initialize()
        
        # Get context that was used for the original query
        query_embedding = await embedding_service.embed_text(query)
        
        context_results = await weaviate.search_similar(
            query_embedding=query_embedding,
            limit=10,
            threshold=0.6,
            filters={}
        )
        
        # Analyze which parts of the response might come from which sources
        response_sentences = response.split('.')
        explanations = []
        
        for result in context_results[:5]:  # Top 5 sources
            # Simple relevance scoring (could be improved with more sophisticated methods)
            content_words = set(result["content"].lower().split())
            
            relevant_sentences = []
            for sentence in response_sentences:
                sentence_words = set(sentence.lower().split())
                overlap = len(content_words.intersection(sentence_words))
                if overlap > 2:  # Threshold for relevance
                    relevant_sentences.append(sentence.strip())
            
            if relevant_sentences:
                explanations.append({
                    "source": {
                        "filename": result["metadata"].get("filename", "Unknown"),
                        "content_preview": result["content"][:200] + "...",
                        "relevance_score": result["score"]
                    },
                    "influenced_parts": relevant_sentences
                })
        
        return {
            "query": query,
            "response": response,
            "explanations": explanations,
            "total_sources_analyzed": len(context_results)
        }
        
    except Exception as e:
        logger.error(f"❌ Explanation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """
    Get chat history for a session
    
    TODO: Implement session management and persistent chat history
    """
    # For now, return empty history
    return {
        "session_id": session_id,
        "messages": [],
        "created_at": None,
        "last_updated": None
    }


@router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    """
    Clear chat history for a session
    
    TODO: Implement session management
    """
    return {
        "message": "Chat history cleared",
        "session_id": session_id
    }


async def _generate_llm_response(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1000,
    temperature: float = 0.7
) -> str:
    """
    Generate response using Ollama LLM
    
    This function communicates with the Ollama service to generate responses.
    """
    try:
        ollama_url = os.getenv("OLLAMA_URL", "http://ollama-service:11434")
        model_name = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
        
        # Prepare the request for Ollama
        ollama_request = {
            "model": model_name,
            "prompt": f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        # Make request to Ollama
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json=ollama_request
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama request failed: {response.status_code} - {response.text}")
                raise Exception(f"LLM service error: {response.status_code}")
            
            result = response.json()
            return result.get("response", "I apologize, but I couldn't generate a response.")
            
    except httpx.TimeoutException:
        logger.error("Ollama request timed out")
        raise Exception("LLM service timeout")
    except httpx.RequestError as e:
        logger.error(f"Ollama request error: {e}")
        raise Exception("LLM service unavailable")
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        # Return a fallback response instead of failing completely
        return "I apologize, but I'm having trouble generating a response right now. Please try again later."


@router.get("/models")
async def list_available_models():
    """
    List available LLM models
    
    Returns the models available in the Ollama service.
    """
    try:
        ollama_url = os.getenv("OLLAMA_URL", "http://ollama-service:11434")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            
            if response.status_code == 200:
                models_data = response.json()
                return {
                    "models": models_data.get("models", []),
                    "current_model": os.getenv("OLLAMA_MODEL", "llama3.2:latest")
                }
            else:
                return {
                    "models": [],
                    "current_model": os.getenv("OLLAMA_MODEL", "llama3.2:latest"),
                    "error": "Could not fetch models from Ollama service"
                }
                
    except Exception as e:
        logger.error(f"❌ Failed to list models: {e}")
        return {
            "models": [],
            "current_model": os.getenv("OLLAMA_MODEL", "llama3.2:latest"),
            "error": str(e)
        } 