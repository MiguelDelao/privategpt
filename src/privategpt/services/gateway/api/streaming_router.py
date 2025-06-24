"""
Streaming endpoints that use token-based authentication.
No JWT middleware - the stream token IS the authentication.
"""

import logging
from typing import AsyncGenerator
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{stream_token}")
async def stream_conversation(stream_token: str):
    """
    Stream the LLM response using a pre-created stream session.
    The stream token provides all authentication needed.
    """
    from privategpt.services.gateway.core.stream_session import StreamSessionManager
    from privategpt.services.gateway.core.xml_parser import parse_ai_content
    from privategpt.shared.settings import settings
    
    logger.info(f"Stream endpoint called with token: {stream_token}")
    
    stream_manager = StreamSessionManager()
    
    # Validate stream token (this is the only auth needed)
    stream_session = await stream_manager.get_session(stream_token)
    if not stream_session:
        logger.error(f"Stream session not found for token: {stream_token}")
        raise HTTPException(status_code=404, detail="Invalid or expired stream token")
    
    logger.info(f"Stream session found for conversation: {stream_session.conversation_id}")
    
    async def event_stream() -> AsyncGenerator[str, None]:
        import json
        from privategpt.infra.tasks.celery_app import save_assistant_message_task
        
        try:
            # Send initial events
            yield f"data: {json.dumps({'type': 'stream_start', 'conversation_id': stream_session.conversation_id})}\n\n"
            
            yield f"data: {json.dumps({'type': 'user_message', 'message': {'id': stream_session.user_message_id, 'role': 'user', 'content': stream_session.llm_messages[-1]['content'], 'created_at': datetime.utcnow().isoformat()}})}\n\n"
            
            yield f"data: {json.dumps({'type': 'assistant_message_start', 'message_id': stream_session.assistant_message_id})}\n\n"
            
            # Stream from LLM service via proxy
            from privategpt.services.gateway.core.proxy import get_proxy
            import httpx
            
            proxy = get_proxy()
            full_content = ""
            
            # Prepare the request for LLM service
            # Convert messages to the format expected by LLM service
            formatted_messages = []
            for msg in stream_session.llm_messages:
                formatted_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            
            llm_request = {
                "model": stream_session.model_name,
                "messages": formatted_messages,
                "temperature": stream_session.temperature,
                "max_tokens": stream_session.max_tokens
            }
            
            # Stream from LLM service
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{proxy.service_urls['llm']}/chat/stream",
                    json=llm_request,
                    timeout=300.0
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            # LLM service returns raw text chunks, not JSON
                            if data:
                                full_content += data
                                yield f"data: {json.dumps({'type': 'content_chunk', 'message_id': stream_session.assistant_message_id, 'content': data})}\n\n"
            
            # Parse the complete response
            parsed_content = parse_ai_content(full_content, settings.enable_thinking_mode)
            
            # Estimate tokens (simplified for now)
            prompt_tokens = sum(len(msg.get("content", "").split()) * 1.3 for msg in stream_session.llm_messages)
            completion_tokens = len(full_content.split()) * 1.3
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'assistant_message_complete', 'message_id': stream_session.assistant_message_id, 'content': parsed_content.processed_content, 'thinking': parsed_content.thinking_content, 'ui_tags': parsed_content.ui_tags})}\n\n"
            
            # Queue background task to save assistant message
            save_assistant_message_task.delay(
                conversation_id=stream_session.conversation_id,
                message_id=stream_session.assistant_message_id,
                content=parsed_content.processed_content,
                raw_content=parsed_content.raw_content,
                thinking_content=parsed_content.thinking_content,
                token_count=int(completion_tokens),
                data={
                    "model_name": stream_session.model_name,
                    "prompt_tokens": int(prompt_tokens),
                    "completion_tokens": int(completion_tokens),
                    "total_tokens": int(prompt_tokens + completion_tokens)
                }
            )
            
            # Clean up the stream session
            await stream_manager.delete_session(stream_token)
            
            # Send final event
            yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in stream: {e}", exc_info=True)
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/debug/{stream_token}")
async def debug_stream_session(stream_token: str):
    """Debug endpoint to check stream session data"""
    from privategpt.services.gateway.core.stream_session import StreamSessionManager
    
    try:
        stream_manager = StreamSessionManager()
        stream_session = await stream_manager.get_session(stream_token)
        
        if not stream_session:
            return {"error": "Stream session not found", "token": stream_token}
        
        return {
            "success": True,
            "session": {
                "token": stream_session.token,
                "conversation_id": stream_session.conversation_id,
                "user_id": stream_session.user_id,
                "model_name": stream_session.model_name,
                "created_at": stream_session.created_at.isoformat() if stream_session.created_at else None
            }
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }