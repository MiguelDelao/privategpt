from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from privategpt.infra.http.log_middleware import RequestLogMiddleware

from privategpt.infra.database.models import Base
from privategpt.infra.database.session import engine
from privategpt.services.auth.api import auth_router

# create FastAPI app
app = FastAPI(title="PrivateGPT Auth v2", version="2.0.0")

# ensure tables exist even if the first import-time call happened before the DB was reachable

@app.on_event("startup")
def _init_db() -> None:  # noqa: D401
    """Ensure tables exist once the DB is reachable.

    In containers the Postgres service may still be starting when the Auth
    container boots.  We attempt to connect a few times before giving up so
    that the service does not crash on a transient error.
    """

    import logging, time
    from sqlalchemy.exc import OperationalError

    max_attempts = 10
    for attempt in range(1, max_attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logging.info("DB connected", attempts=attempt)
            break
        except OperationalError as exc:
            logging.warning(
                f"DB not ready, retrying ({attempt}/{max_attempts}) - {str(exc)[:120]}"
            )
            time.sleep(2)
        except Exception as exc:
            logging.exception("Failed to create tables on startup", exc_info=exc)
            break

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True
)
app.add_middleware(RequestLogMiddleware)
app.include_router(auth_router.router)

@app.get("/")
async def root():
    return {"service": "auth-v2", "status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 