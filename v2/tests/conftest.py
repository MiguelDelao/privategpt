import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from privategpt.infra.database.models import Base
from privategpt.infra.database.session import get_db as real_get_db

# --------------------------------------------------
# Database fixture (in-memory SQLite for unit tests)
# --------------------------------------------------
@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()

# --------------------------------------------------
# Monkeypatch FastAPI dependency to use the test session
# --------------------------------------------------
@pytest.fixture(scope="function", autouse=True)
def _override_get_db(db_session, monkeypatch):
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass
    monkeypatch.setattr(
        "privategpt.infra.database.session.get_db", _get_db_override, raising=True
    ) 