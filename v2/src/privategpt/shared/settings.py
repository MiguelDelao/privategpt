from __future__ import annotations

"""Shared configuration proxy wrapping legacy config_loader.

This is identical to the implementation in the legacy refactor branch and
will be replaced by a pydantic.Settings object later.
"""

from functools import lru_cache

try:
    from config_loader import ConfigLoader, get_config_loader  # type: ignore
except ModuleNotFoundError as exc:
    raise ImportError("config_loader module missing; run from project root during migration") from exc


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