from __future__ import annotations

from typing import List

from privategpt.core.ports.text_splitter import TextSplitterPort


class SimpleSplitterAdapter(TextSplitterPort):
    """Very naive splitter that chunks text by paragraphs (double newline)."""

    def split(self, text: str) -> List[str]:
        return [part.strip() for part in text.split("\n\n") if part.strip()] 