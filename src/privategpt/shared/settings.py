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

from functools import lru_cache

try:
    # Root-level module keeps working until we migrate it into the
    # shared package.
    from config_loader import ConfigLoader, get_config_loader  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – should not happen
    raise ImportError(
        "config_loader module not found. Ensure you run this package from the project root while the refactor is ongoing."
    )


class _LazySettings:
    """Proxy exposing attribute access directly to ConfigLoader.get()."""

    _loader: ConfigLoader

    def __init__(self) -> None:
        self._loader = get_config_loader()

    def __getattr__(self, item):  # noqa: Dunder
        # Delegate attribute access to dot-notation lookup.
        try:
            return self._loader.get(item)
        except Exception as exc:
            raise AttributeError(item) from exc

    def get(self, key: str, default=None):
        """Explicit getter mirroring original ConfigLoader API."""
        return self._loader.get(key, default)


@lru_cache(maxsize=1)
def instance() -> _LazySettings:  # noqa: D401 – imperative function name is fine here
    """Return a singleton of :class:`_LazySettings`."""

    return _LazySettings()


# Public alias that new code can import.
settings = instance() 