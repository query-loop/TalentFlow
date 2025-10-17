"""Chroma client wrapper with optional real chromadb support.

Configuration via environment variables:
- TF_USE_FAKE_CHROMA=1 (default) to use an in-memory fake collection for tests/dev
- TF_EMBED_MODEL to choose sentence-transformers model when available
- CHROMA_DIR to control chromadb persist directory
"""
from __future__ import annotations

import os
from typing import List, Dict, Any, Optional

USE_FAKE = os.environ.get("TF_USE_FAKE_CHROMA", "1") == "1"


class FakeCollection:
    def __init__(self):
        self._docs: Dict[str, Dict[str, Any]] = {}

    def upsert(self, ids: List[str], metadatas: List[Dict[str, Any]], documents: List[str], embeddings=None):
        for i, _id in enumerate(ids):
            self._docs[_id] = {
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "text": documents[i] if i < len(documents) else "",
                "embedding": embeddings[i] if embeddings and i < len(embeddings) else None,
            }

    def query(self, query_embeddings=None, n_results=5, include=None):
        docs = list(self._docs.values())[:n_results]
        return {"documents": [[d["text"] for d in docs]], "metadatas": [[d["metadata"] for d in docs]], "distances": [[0.0 for _ in docs]]}


class ChromaClient:
    def __init__(self, collection_name: str = "talent_chunks"):
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        if USE_FAKE:
            self._collection = FakeCollection()
        else:
            try:
                import chromadb
                from chromadb.config import Settings

                CHROMA_DIR = os.environ.get("CHROMA_DIR", ".chroma")
                self._client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=CHROMA_DIR))
                # ensure collection exists
                existing = [c.name for c in self._client.list_collections()]
                if collection_name in existing:
                    self._collection = self._client.get_collection(collection_name)
                else:
                    self._collection = self._client.create_collection(name=collection_name)
            except Exception as e:
                # fall back to fake if chromadb fails
                print("chromadb unavailable or failed to initialize, using fake collection:", e)
                self._collection = FakeCollection()

    def get_collection(self):
        return self._collection

    def persist(self):
        # If using chromadb client with persistence, persist to disk
        if self._client is not None:
            try:
                self._client.persist()
            except Exception:
                pass


def _simple_embed(texts: List[str]):
    out = []
    for t in texts:
        tokens = t.split()
        vec = [0] * 8
        for i, w in enumerate(tokens[:8]):
            vec[i] = len(w) % 10
        out.append([float(x) for x in vec])
    return out


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Attempt to use sentence-transformers; otherwise fall back to simple deterministic embedder."""
    try:
        from sentence_transformers import SentenceTransformer
        model_name = os.environ.get("TF_EMBED_MODEL", "all-MiniLM-L6-v2")
        model = SentenceTransformer(model_name)
        vecs = model.encode(texts, show_progress_bar=False).tolist()
        return vecs
    except Exception:
        return _simple_embed(texts)


def upsert_chunks(collection, candidate_id: str, chunks: List[Dict[str, Any]]):
    texts = [c["text"] for c in chunks]
    ids = [f"{candidate_id}::{c['id']}" for c in chunks]
    metadatas = [c.get("metadata", {}) for c in chunks]
    embeddings = embed_texts(texts)
    collection.upsert(ids=ids, metadatas=metadatas, documents=texts, embeddings=embeddings)


def query_similar(collection, query_text: str, top_k: int = 5) -> Dict[str, Any]:
    qv = embed_texts([query_text])[0]
    try:
        res = collection.query(query_embeddings=[qv], n_results=top_k, include=["documents", "metadatas", "distances"])
        return res
    except Exception:
        # Fallback for FakeCollection
        return collection.query(query_embeddings=[qv], n_results=top_k, include=["documents", "metadatas", "distances"])
