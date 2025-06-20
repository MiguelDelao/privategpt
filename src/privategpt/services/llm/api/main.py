from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from privategpt.services.llm.adapters.ollama_adapter import OllamaAdapter
from privategpt.services.llm.adapters.echo import EchoAdapter
from privategpt.services.llm.core import LLMPort
from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)

app = FastAPI(title="PrivateGPT LLM Service", version="0.2.0")

# Provider factory
def create_adapter() -> LLMPort:
    """Create LLM adapter based on configuration."""
    provider = settings.llm_provider
    base_url = settings.llm_base_url
    
    if not provider:
        logger.warning("No LLM provider configured, using Echo adapter for testing")
        return EchoAdapter()
    
    if provider.lower() == "ollama":
        if not base_url:
            raise ValueError("llm_base_url must be configured for Ollama provider")
        return OllamaAdapter(base_url=base_url)
    elif provider.lower() == "echo":
        return EchoAdapter()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

# Initialize adapter
try:
    adapter = create_adapter()
    logger.info(f"Using {adapter.__class__.__name__} with provider: {settings.llm_provider}")
except Exception as e:
    logger.error(f"Failed to initialize LLM adapter: {e}. Using Echo adapter.")
    adapter = EchoAdapter()


class GenerateRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, gt=0)
    stop: Optional[List[str]] = None


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, gt=0)
    stop: Optional[List[str]] = None


class GenerateResponse(BaseModel):
    text: str
    model: str


class ModelInfo(BaseModel):
    name: str
    size: Optional[int] = None
    modified_at: Optional[str] = None


@app.post("/generate", response_model=GenerateResponse)
async def generate(data: GenerateRequest):
    """Generate a single response to a prompt."""
    try:
        kwargs = {k: v for k, v in data.model_dump().items() if v is not None and k != "prompt"}
        text = await adapter.generate(data.prompt, **kwargs)
        return GenerateResponse(
            text=text,
            model=kwargs.get("model", settings.llm_default_model)
        )
    except Exception as e:
        logger.error(f"Generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/stream")
async def generate_stream(data: GenerateRequest):
    """Generate a streaming response to a prompt."""
    try:
        kwargs = {k: v for k, v in data.model_dump().items() if v is not None and k != "prompt"}
        
        async def stream_generator():
            try:
                async for chunk in adapter.generate_stream(data.prompt, **kwargs):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: Error: {str(e)}\n\n"
                
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        logger.error(f"Stream setup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=GenerateResponse)
async def chat(data: ChatRequest):
    """Generate response for a conversation."""
    try:
        kwargs = {k: v for k, v in data.model_dump().items() if v is not None and k != "messages"}
        messages = [{"role": msg.role, "content": msg.content} for msg in data.messages]
        text = await adapter.chat(messages, **kwargs)
        return GenerateResponse(
            text=text,
            model=kwargs.get("model", settings.llm_default_model)
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(data: ChatRequest):
    """Generate streaming response for a conversation."""
    try:
        kwargs = {k: v for k, v in data.model_dump().items() if v is not None and k != "messages"}
        messages = [{"role": msg.role, "content": msg.content} for msg in data.messages]
        
        async def stream_generator():
            try:
                async for chunk in adapter.chat_stream(messages, **kwargs):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Chat stream error: {e}")
                yield f"data: Error: {str(e)}\n\n"
                
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        logger.error(f"Chat stream setup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models", response_model=List[ModelInfo])
async def get_models():
    """Get available models."""
    try:
        models = await adapter.get_models()
        return [ModelInfo(**model) for model in models]
    except Exception as e:
        logger.error(f"Models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        healthy = await adapter.health_check()
        if healthy:
            return {"status": "healthy", "service": "llm"}
        else:
            raise HTTPException(status_code=503, detail="LLM service unhealthy")
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/")
async def root():
    return {
        "service": "llm",
        "version": "0.2.0",
        "status": "ok",
        "adapter": adapter.__class__.__name__,
        "model": settings.llm_default_model
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 