from __future__ import annotations

from abc import abstractmethod
from typing import List, Protocol


class TextSplitter(Protocol):
    """Split raw text into semantically coherent chunks."""

    @abstractmethod
    def split(self, text: str) -> List[str]:
        ...
