from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(slots=True)
class SearchQuery:
    text: str
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 5 