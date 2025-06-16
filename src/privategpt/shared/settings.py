from __future__ import annotations

"""Shared configuration interface.

This is an initial compatibility layer that wraps the existing
``config_loader.ConfigLoader`` implementation so that new code under
``privategpt.*`` can start depending on a stable import path::

    from privategpt.shared.settings import settings

The long-term goal is to replace this wrapper with a pydantic-based
``Settings`` object that directly consumes environment variables and any
Redis overrides.  For now we expose the original loader to avoid
breaking the current services while the monorepo refactor is in
progress.
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseSettings, Field, validator

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
_CONFIG_ENV = "PRIVATEGPT_CONFIG_FILE"
_DEFAULT_CONFIG_FILE = "config.json"


def _read_config_file() -> Dict[str, Any]:
    """Return the contents of *config.json* (or user-supplied file) as a dict.

    The file path can be overridden with the ``PRIVATEGPT_CONFIG_FILE`` env var.
    If the file is missing or malformed an empty dict is returned and a warning
    is printed.  *All* keys are treated as **lower-case** for predictable look-ups.
    """
    path = Path(os.getenv(_CONFIG_ENV, _DEFAULT_CONFIG_FILE)).expanduser().resolve()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
    except Exception as exc:  # noqa: BLE001 – broad but safe here
        print(f"[settings] Could not parse {path}: {exc}. Using defaults.")
        return {}

    # normalise key-case for dot-notation access
    def _lower_keys(obj):
        if isinstance(obj, dict):
            return {k.lower(): _lower_keys(v) for k, v in obj.items()}
        return obj

    return _lower_keys(data)


# ---------------------------------------------------------------------------
# Pydantic settings model (typed access)
# ---------------------------------------------------------------------------


class _CoreSettings(BaseSettings):
    """Authoritative configuration object.

    Environment variables *always* win over the JSON file so containerised
    deployments can inject secrets without baking them in the image.
    """

    # ------------------------------------------------------------------
    # GLOBAL
    # ------------------------------------------------------------------
    log_level: str = Field("INFO", alias="log_level", env="LOG_LEVEL")

    # ------------------------------- DATABASE & CACHES ----------------
    database_url: str = Field("sqlite+aiosqlite:///./privategpt.db", alias="database_url", env="DATABASE_URL")
    redis_url: Optional[str] = Field(None, alias="redis_url", env="REDIS_URL")
    weaviate_url: str = Field("http://weaviate-db:8080", alias="weaviate_url", env="WEAVIATE_URL")

    # ------------------------------- LLM / EMBEDDING ------------------
    ollama_url: Optional[str] = Field(None, alias="ollama_url", env="OLLAMA_URL")
    ollama_model: Optional[str] = Field(None, alias="ollama_model", env="OLLAMA_MODEL")
    embed_model: str = Field("BAAI/bge-small-en-v1.5", alias="embed_model", env="EMBED_MODEL")

    # allow arbitrary extra keys so the JSON can contain service-specific blocks
    model_config = dict(extra="allow", case_sensitive=False)

    # auto-strip surrounding spaces for strings
    @validator("database_url", "redis_url", "weaviate_url", "ollama_url", pre=True)
    @classmethod
    def _strip(cls, v):  # noqa: D401 – fine for validator
        if isinstance(v, str):
            return v.strip()
        return v


# ---------------------------------------------------------------------------
# Public lazy proxy to keep *existing* import paths working
# ---------------------------------------------------------------------------


class _LazySettings:  # noqa: D101 – internal helper
    _model: _CoreSettings
    _raw_data: Dict[str, Any]

    def __init__(self) -> None:
        self._raw_data = _read_config_file()
        # feed JSON data into Pydantic; env vars override automatically
        self._model = _CoreSettings(**self._raw_data)

    # ------------------ dotted access helper -------------------------
    def get(self, key: str, default: Any = None) -> Any:  # noqa: D401 – heritage API
        """Mimic the legacy ``settings.get('section.key')`` helper.

        1.  Looks for an **environment variable** matching the key but in
            ``UPPER_SNAKE`` case (``database.url`` -> ``DATABASE_URL``).
        2.  Falls back to the JSON config dict.
        3.  Returns *default* if nothing is found.
        """
        env_key = key.replace(".", "_").upper()
        if env_key in os.environ:
            return os.environ[env_key]

        # descend into raw JSON data (already lower-cased)
        cur: Any = self._raw_data
        for part in key.lower().split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    # ------------------ attribute proxy ------------------------------
    def __getattr__(self, item: str):  # noqa: D401 – dyn attr proxy
        # delegate to pydantic model (typed fields)
        try:
            return getattr(self._model, item)
        except AttributeError as exc:
            raise AttributeError(item) from exc

    # allow dict-like access to extra keys defined in JSON
    def __getitem__(self, item: str):  # type: ignore[override]
        return self.get(item)


@lru_cache(maxsize=1)
def _instance() -> _LazySettings:  # noqa: D401
    return _LazySettings()


# Public singleton used across the codebase
settings = _instance()

__all__ = ["settings"] 