# Core utilities always available
from .settings import settings  # noqa: F401
from .logging import get_logger  # noqa: F401

# Optional security helpers (require *bcrypt* & *python-jose*)
try:
    from .security import hash_password, verify_password, create_access_token, decode_token  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover – optional deps absent in minimal env
    # expose dummies so `from privategpt.shared import hash_password` still works
    def _unavailable(*_args, **_kwargs):  # noqa: D401 – placeholder
        raise RuntimeError("Security helpers are unavailable – install 'bcrypt' & 'python-jose'.")

    hash_password = verify_password = create_access_token = decode_token = _unavailable  # type: ignore

# Optional HTTP auth client (depends on httpx, etc.) – ignore if not installed
try:
    from .auth_client import AuthServiceClient  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    AuthServiceClient = None  # type: ignore

__all__ = [
    "settings",
    "get_logger",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    "AuthServiceClient",
]
