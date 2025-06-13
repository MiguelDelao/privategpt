from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router as auth_router
from ...infra.database.models import Base
from ...infra.database.session import engine

# Create tables if not exist (ideally Alembic migrations in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PrivateGPT Auth Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/")
async def root():
    return {"service": "auth-service", "status": "ok"}


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000) 