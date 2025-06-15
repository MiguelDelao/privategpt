from __future__ import annotations

import os
import asyncio
from typing import Sequence, List
import logging

from sentence_transformers import SentenceTransformer
import torch

from privategpt.core.ports.embedder import EmbedderPort

logger = logging.getLogger(__name__)


class BgeEmbedderAdapter(EmbedderPort):
    """Sentence-Transformers BGE embedder with async wrappers."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model: SentenceTransformer | None = None

    async def _ensure_model(self) -> SentenceTransformer:
        if self._model is not None:
            return self._model

        def _load() -> SentenceTransformer:
            logger.info(f"Loading embedder {self.model_name} on {self.device}")
            return SentenceTransformer(self.model_name, device=self.device)

        self._model = await asyncio.to_thread(_load)
        return self._model

    async def embed_documents(self, texts: List[str]) -> List[Sequence[float]]:
        model = await self._ensure_model()

        def _encode(batch: List[str]):
            with torch.no_grad():
                return model.encode(batch, convert_to_numpy=True, normalize_embeddings=True).tolist()

        return await asyncio.to_thread(_encode, texts)

    async def embed_query(self, text: str) -> Sequence[float]:
        model = await self._ensure_model()

        def _encode_one(txt: str):
            with torch.no_grad():
                return model.encode(txt, convert_to_numpy=True, normalize_embeddings=True).tolist()

        return await asyncio.to_thread(_encode_one, text) 