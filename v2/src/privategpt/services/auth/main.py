from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from privategpt.infra.database.models import Base
from privategpt.infra.database.session import engine
from privategpt.services.auth.routers import auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="PrivateGPT Auth v2", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True
)
app.include_router(auth_router.router)

@app.get("/")
async def root():
    return {"service": "auth-v2", "status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 