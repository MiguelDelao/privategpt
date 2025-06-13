from __future__ import annotations

from privategpt.core.ports.text_splitter import TextSplitter

try:
    from docker.knowledge_service.app.services.chunking import (  # type: ignore
        split_text_into_chunks,
    )
except ImportError:
    split_text_into_chunks = None  # type: ignore


class DefaultTextSplitter(TextSplitter):
    """Adapter that delegates to the legacy `split_text_into_chunks` util."""

    def split(self, text: str):  # type: ignore[override]
        if split_text_into_chunks:
            return [c["content"] for c in split_text_into_chunks(text)]
        # naive fallback
        chunk_size = 1024
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] 