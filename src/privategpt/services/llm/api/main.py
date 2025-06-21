from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from privategpt.services.llm.core.model_registry import get_model_registry
from privategpt.services.llm.core.provider_factory import LLMProviderFactory
from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)

app = FastAPI(title="PrivateGPT LLM Service", version="0.2.0")

# Initialize model registry
model_registry = get_model_registry()

@app.on_event("startup")
async def initialize_providers():
    """Initialize all LLM providers."""
    try:
        await LLMProviderFactory.initialize_model_registry()
        logger.info("Model registry initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize model registry: {e}")


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


class ModelResponse(BaseModel):
    name: str
    provider: str
    type: str
    available: bool = True
    description: Optional[str] = None
    parameter_size: Optional[str] = None
    capabilities: List[str] = []
    cost_per_token: Optional[float] = None


@app.post("/generate", response_model=GenerateResponse)
async def generate(data: GenerateRequest):
    """Generate a single response to a prompt."""
    try:
        kwargs = {k: v for k, v in data.model_dump().items() if v is not None and k not in ["prompt", "model"]}
        model_name = data.model or settings.llm_default_model
        
        # Convert prompt to messages format for model registry
        messages = [{"role": "user", "content": data.prompt}]
        text = await model_registry.chat(model_name, messages, **kwargs)
        
        return GenerateResponse(
            text=text,
            model=model_name
        )
    except Exception as e:
        logger.error(f"Generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/stream")
async def generate_stream(data: GenerateRequest):
    """Generate a streaming response to a prompt."""
    try:
        kwargs = {k: v for k, v in data.model_dump().items() if v is not None and k not in ["prompt", "model"]}
        model_name = data.model or settings.llm_default_model
        
        async def stream_generator():
            try:
                # Convert prompt to messages format for model registry
                messages = [{"role": "user", "content": data.prompt}]
                async for chunk in model_registry.chat_stream(model_name, messages, **kwargs):
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
        kwargs = {k: v for k, v in data.model_dump().items() if v is not None and k not in ["messages", "model"]}
        model_name = data.model or settings.llm_default_model
        messages = [{"role": msg.role, "content": msg.content} for msg in data.messages]
        
        text = await model_registry.chat(model_name, messages, **kwargs)
        return GenerateResponse(
            text=text,
            model=model_name
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(data: ChatRequest):
    """Generate streaming response for a conversation."""
    try:
        kwargs = {k: v for k, v in data.model_dump().items() if v is not None and k not in ["messages", "model"]}
        model_name = data.model or settings.llm_default_model
        messages = [{"role": msg.role, "content": msg.content} for msg in data.messages]
        
        async def stream_generator():
            try:
                async for chunk in model_registry.chat_stream(model_name, messages, **kwargs):
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


@app.get("/models", response_model=List[ModelResponse])
async def get_models():
    """Get available models from all providers."""
    try:
        models = await model_registry.get_all_models()
        return [
            ModelResponse(
                name=model.name,
                provider=model.provider,
                type=model.type,
                available=model.available,
                description=model.description,
                parameter_size=model.parameter_size,
                capabilities=model.capabilities or [],
                cost_per_token=model.cost_per_token
            )
            for model in models
        ]
    except Exception as e:
        logger.error(f"Models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_status = await model_registry.health_check()
        
        if health_status["overall_status"] == "healthy":
            return {
                "status": "healthy", 
                "service": "llm",
                "providers": health_status["providers"],
                "total_models": health_status["total_models"]
            }
        else:
            return {
                "status": "degraded",
                "service": "llm", 
                "providers": health_status["providers"],
                "total_models": health_status["total_models"]
            }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/")
async def root():
    try:
        providers = model_registry.get_registered_providers()
        health_status = await model_registry.health_check()
        return {
            "service": "llm",
            "version": "0.2.0",
            "status": "ok",
            "providers": providers,
            "total_models": health_status.get("total_models", 0),
            "default_model": settings.llm_default_model
        }
    except Exception as e:
        logger.error(f"Root endpoint error: {e}")
        return {
            "service": "llm",
            "version": "0.2.0",
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 