from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from privategpt.services.llm.adapters.echo import EchoAdapter

app = FastAPI(title="PrivateGPT LLM Service", version="0.1.0")

adapter = EchoAdapter()


class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    text: str


@app.post("/generate", response_model=GenerateResponse)
async def generate(data: GenerateRequest):
    text = await adapter.generate(data.prompt)
    return GenerateResponse(text=text)


@app.get("/")
async def root():
    return {"service": "llm", "status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001) 