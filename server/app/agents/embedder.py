"""Embedder Agent

Provides a pluggable embedder that can use local `sentence-transformers`, OpenAI
Embeddings (if API key configured), or a deterministic fallback (hash-based)
for tests and light-weight environments.
"""
from __future__ import annotations

from typing import List, Optional
import hashlib
import logging

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    _HAS_ST = True
except Exception:
    SentenceTransformer = None
    np = None
    _HAS_ST = False

try:
    import openai
    _HAS_OPENAI = True
except Exception:
    openai = None
    _HAS_OPENAI = False

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self, model_name: Optional[str] = None, openai_model: Optional[str] = "text-embedding-3-small"):
        # prefer local ST model if available
        self.st_model_name = model_name or "all-MiniLM-L6-v2"
        self._st = None
        if _HAS_ST and self.st_model_name:
            try:
                self._st = SentenceTransformer(self.st_model_name)
            except Exception:
                logger.exception("Failed to load sentence-transformers model; falling back")
                self._st = None

        self.openai_model = openai_model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        # Try OpenAI first if configured and env available
        if _HAS_OPENAI and openai is not None and self.openai_model:
            try:
                resp = openai.Embedding.create(input=texts, model=self.openai_model)
                return [d["embedding"] for d in resp["data"]]
            except Exception:
                logger.exception("OpenAI embedding failed; falling back")

        if self._st is not None:
            try:
                arr = self._st.encode(texts, convert_to_numpy=True)
                # convert numpy arrays to lists
                return [list(a.astype(float)) for a in arr]
            except Exception:
                logger.exception("SentenceTransformer embedding failed; falling back")

        # Deterministic fallback: use a hashed pseudo-embedding (small dim)
        return [self._hash_embed(t) for t in texts]

    def _hash_embed(self, text: str, dim: int = 8) -> List[float]:
        h = hashlib.blake2b(text.encode("utf-8"), digest_size=dim)
        bs = h.digest()
        # convert bytes to floats in [0,1]
        return [b / 255.0 for b in bs]


def embed_texts(texts: List[str], model_name: Optional[str] = None) -> List[List[float]]:
    e = Embedder(model_name=model_name)
    return e.embed_texts(texts)
