from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(slots=True)
class Chunk:
    id: int | None
    document_id: int
    position: int  # order within original doc
    text: str
    embedding: Sequence[float] | None = None 