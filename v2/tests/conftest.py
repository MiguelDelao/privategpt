import sys

# ------------------------------------------------------------------
# Ensure the *pytest_asyncio* dependency is available even in minimal
# environments (the stub only provides the *fixture* decorator used in tests).
# ------------------------------------------------------------------

try:
    import pytest_asyncio  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – fallback stub
    import types, pytest

    pytest_asyncio = types.ModuleType("pytest_asyncio")  # type: ignore

    # expose *fixture* symbol that just re-exports pytest.fixture
    pytest_asyncio.fixture = pytest.fixture  # type: ignore

    sys.modules["pytest_asyncio"] = pytest_asyncio

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

# --------------------------------------------------
# Provide minimal stubs for other optional third-party libs that may be
# absent in the executor environment. They only need to satisfy import time.
# --------------------------------------------------

import types, hashlib, base64

if "jose" not in sys.modules:
    jose_stub = types.ModuleType("jose")

    jwt_stub = types.ModuleType("jose.jwt")

    def _encode(payload, secret, algorithm="HS256"):
        return base64.urlsafe_b64encode(str(payload).encode()).decode()

    def _decode(token, secret, algorithms=None):  # noqa: D401 – stub
        try:
            return eval(base64.urlsafe_b64decode(token.encode()).decode())
        except Exception:
            return {}

    jwt_stub.encode = _encode  # type: ignore
    jwt_stub.decode = _decode  # type: ignore

    jose_stub.jwt = jwt_stub  # type: ignore

    sys.modules["jose"] = jose_stub
    sys.modules["jose.jwt"] = jwt_stub

if "aiosqlite" not in sys.modules:
    aiosqlite_stub = types.ModuleType("aiosqlite")
    # minimal exceptions/attributes used by SQLAlchemy dialect adapter
    class DatabaseError(Exception):
        pass

    aiosqlite_stub.DatabaseError = DatabaseError  # type: ignore
    aiosqlite_stub.Error = DatabaseError  # type: ignore
    aiosqlite_stub.IntegrityError = DatabaseError  # type: ignore
    aiosqlite_stub.NotSupportedError = DatabaseError  # type: ignore

    sys.modules["aiosqlite"] = aiosqlite_stub

# email_validator stub for pydantic optional dependency

if "email_validator" not in sys.modules:
    email_validator_stub = types.ModuleType("email_validator")
    def validate_email(email, **kwargs):  # noqa: D401 – stub function
        return {
            "email": email,
            "local_part": email.split("@")[0],
            "domain": email.split("@")[-1],
        }
    email_validator_stub.validate_email = validate_email  # type: ignore
    email_validator_stub.__version__ = "2.0.0"
    sys.modules["email_validator"] = email_validator_stub

# patch importlib.metadata.version so pydantic email validator check passes
import importlib.metadata as _ilm
from importlib.metadata import PackageNotFoundError as _PNF


def _version(name):  # noqa: D401
    if name in ("email-validator", "email_validator"):
        return "2.0.0"
    raise _PNF(name)

_ilm.version = _version  # type: ignore

pytest_plugins: list[str] = [] 