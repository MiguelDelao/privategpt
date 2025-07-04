from __future__ import annotations

"""Unified settings object for v2.

This replaces the legacy *config_loader*-backed implementation with a plain
`pydantic.BaseSettings` powered model that reads from environment variables
(and, optionally, the root *config.json*).  It lives in *v2/src/privategpt* so
it wins the import-resolution order when both v1 and v2 are on `PYTHONPATH`.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict
import json
import os

# We prefer the standalone *pydantic-settings* package (pydantic ≥2.5) but fall
# back to `pydantic.BaseSettings` if the extra package is missing (helps during
# unit-test execution without installing optional deps).
from pydantic import Field, field_validator

try:
    from pydantic_settings import BaseSettings  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – fallback path
    from pydantic import BaseModel

    class _FallbackBaseSettings(BaseModel):  # type: ignore
        """Very thin replacement so tests can run without *pydantic-settings*."""

        # allow arbitrary attributes like BaseSettings does
        model_config = {
            "extra": "allow",
        }

        def __init__(self, **data):  # noqa: D401 – mirror BaseSettings API
            super().__init__(**data)

    BaseSettings = _FallbackBaseSettings  # type: ignore

_CONFIG_ENV = "PRIVATEGPT_CONFIG_FILE"
_DEFAULT_CONFIG_FILE = "config.json"


def _read_config_file() -> Dict[str, Any]:  # noqa: D401 – internal helper
    path = Path(os.getenv(_CONFIG_ENV, _DEFAULT_CONFIG_FILE)).expanduser().resolve()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fp:
            raw = json.load(fp)
    except Exception:  # noqa: BLE001 – tolerate user edits
        return {}

    # lowercase keys recursively for dot-notation look-ups
    def _lower(obj: Any):  # type: ignore[return-type]
        if isinstance(obj, dict):
            return {k.lower(): _lower(v) for k, v in obj.items()}
        return obj

    return _lower(raw)


# ruff/flake8 will flag too-many-attributes but that's acceptable here.
class _CoreSettings(BaseSettings):
    # GLOBAL -----------------------------------------------------------
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # DATABASE & CACHES ----------------------------------------------
    database_url: str = Field("sqlite+aiosqlite:///./privategpt.db", env="DATABASE_URL")
    redis_url: str = Field("redis://redis:6379/0", env="REDIS_URL")
    weaviate_url: str = Field("http://weaviate:8080", env="WEAVIATE_URL")

    # LLM / EMBEDDINGS ----------------------------------------------
    llm_provider: str = Field("", env="LLM_PROVIDER")
    llm_base_url: str = Field("", env="LLM_BASE_URL")
    llm_default_model: str = Field("", env="LLM_DEFAULT_MODEL")
    embed_model: str = Field("BAAI/bge-small-en-v1.5", env="EMBED_MODEL")
    
    # LLM PROVIDERS ------------------------------------------------
    # Ollama (Local Models)
    ollama_enabled: bool = Field(True, env="OLLAMA_ENABLED")
    ollama_base_url: str = Field("http://ollama:11434", env="OLLAMA_BASE_URL") 
    ollama_model: str = Field("llama3.2", env="OLLAMA_MODEL")
    
    # OpenAI (Cloud API)
    openai_enabled: bool = Field(False, env="OPENAI_ENABLED")
    openai_api_key: str = Field("", env="OPENAI_API_KEY")
    openai_base_url: str = Field("https://api.openai.com/v1", env="OPENAI_BASE_URL")
    openai_model: str = Field("gpt-4", env="OPENAI_MODEL")
    openai_models: list[str] = Field([], env="OPENAI_MODELS")
    
    # Anthropic (Claude API)  
    anthropic_enabled: bool = Field(False, env="ANTHROPIC_ENABLED")
    anthropic_api_key: str = Field("", env="ANTHROPIC_API_KEY")
    anthropic_base_url: str = Field("https://api.anthropic.com", env="ANTHROPIC_BASE_URL")
    anthropic_model: str = Field("claude-3-5-sonnet-20241022", env="ANTHROPIC_MODEL")
    anthropic_models: list[str] = Field([], env="ANTHROPIC_MODELS")
    
    # KEYCLOAK / AUTHENTICATION -----------------------------------
    keycloak_url: str = Field("http://keycloak:8080", env="KEYCLOAK_URL")
    keycloak_realm: str = Field("privategpt", env="KEYCLOAK_REALM")
    keycloak_client_id: str = Field("privategpt-ui", env="KEYCLOAK_CLIENT_ID")
    
    # DEFAULT ADMIN USER ----------------------------------------
    default_admin_email: str = Field("admin@admin.com", env="DEFAULT_ADMIN_EMAIL")
    default_admin_username: str = Field("admin@admin.com", env="DEFAULT_ADMIN_USERNAME")
    default_admin_password: str = Field("admin", env="DEFAULT_ADMIN_PASSWORD")
    default_admin_first_name: str = Field("Admin", env="DEFAULT_ADMIN_FIRST_NAME")
    default_admin_last_name: str = Field("User", env="DEFAULT_ADMIN_LAST_NAME")
    
    # SERVICE URLS ------------------------------------------------
    rag_service_url: str = Field("http://rag-service:8000", env="RAG_SERVICE_URL")
    llm_service_url: str = Field("http://llm-service:8000", env="LLM_SERVICE_URL")
    mcp_service_url: str = Field("http://mcp-service:8000", env="MCP_SERVICE_URL")
    
    # MCP CONFIGURATION -------------------------------------------
    mcp_enabled: bool = Field(True, env="MCP_ENABLED")
    mcp_transport: str = Field("stdio", env="MCP_TRANSPORT")  # "stdio" or "http"
    mcp_available_tools: str = Field("*", env="MCP_AVAILABLE_TOOLS")  # "*", "", or "tool1,tool2"
    
    # SYSTEM PROMPTS ---------------------------------------------
    default_system_prompt: str = Field("", env="DEFAULT_SYSTEM_PROMPT")
    enable_prompt_caching: bool = Field(True, env="ENABLE_PROMPT_CACHING")
    enable_thinking_mode: bool = Field(True, env="ENABLE_THINKING_MODE")

    model_config = {
        "extra": "allow",
        "case_sensitive": False,
    }

    @field_validator("database_url", "redis_url", "weaviate_url", "llm_base_url", mode="before")
    @classmethod
    def _strip(cls, v):  # noqa: D401
        if isinstance(v, str):
            return v.strip()
        return v


class _LazySettings:
    """Lazy proxy so we keep a familiar singleton import."""

    _model: _CoreSettings
    _raw_json: Dict[str, Any]

    def __init__(self) -> None:
        self._raw_json = _read_config_file()
        self._model = _CoreSettings(**self._raw_json)

    # dotted-key accessor for legacy usages
    def get(self, key: str, default: Any | None = None) -> Any:  # noqa: D401
        env_key = key.replace(".", "_").upper()
        if env_key in os.environ:
            return os.environ[env_key]

        cur: Any = self._raw_json
        for part in key.lower().split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    def __getattr__(self, item: str):  # noqa: D401
        try:
            return getattr(self._model, item)
        except AttributeError as err:
            raise AttributeError(item) from err


@lru_cache(maxsize=1)
def _instance() -> _LazySettings:  # noqa: D401
    return _LazySettings()


settings = _instance()

__all__ = ["settings"] 