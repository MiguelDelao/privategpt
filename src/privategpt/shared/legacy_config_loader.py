"""Legacy import shim to expose the existing `config_loader` module under the
`privategpt.shared` namespace.

This keeps backward-compatibility *and* allows new code to depend on a stable
import path while we migrate toward a pydantic-based `Settings` object.
"""

from importlib import import_module
from types import ModuleType
import sys as _sys

_module: ModuleType = import_module("config_loader")

# Re-export public names (simplistic: anything not starting with "_")
for _name in dir(_module):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_module, _name)

# Ensure both paths in sys.modules reference the same module instance
_sys.modules[__name__] = _module 