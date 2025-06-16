from __future__ import annotations

"""Shared configuration proxy wrapping legacy config_loader.

This is identical to the implementation in the legacy refactor branch and
will be replaced by a pydantic.Settings object later.
"""

from functools import lru_cache

try:
    from config_loader import ConfigLoader, get_config_loader  # type: ignore
except ModuleNotFoundError:
    # Graceful fallback when running from a sub-directory where `config_loader.py` is not importable
    class _FallbackConfigLoader:  # noqa: D101
        def get(self, key: str, default=None):  # noqa: D401
            # Simply return provided default; environment variable lookup could be added here later
            return default

    ConfigLoader = _FallbackConfigLoader  # type: ignore[assignment]

    def get_config_loader():  # type: ignore[return-type]
        return _FallbackConfigLoader()


class _LazySettings:
    _loader: ConfigLoader

    def __init__(self) -> None:
        self._loader = get_config_loader()

    def __getattr__(self, item):  # noqa: D401
        try:
            return self._loader.get(item)
        except Exception as e:  # noqa: BLE001
            raise AttributeError(item) from e

    def get(self, key: str, default=None):
        return self._loader.get(key, default)


@lru_cache(maxsize=1)
def instance() -> _LazySettings:
    return _LazySettings()


settings = instance() 