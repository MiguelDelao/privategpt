from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict


@dataclass(slots=True)
class Answer:
    text: str
    citations: List[Dict[str, str]] 