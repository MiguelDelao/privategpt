from __future__ import annotations

from typing import Protocol, List


class TextSplitterPort(Protocol):
    def split(self, text: str) -> List[str]: ... 