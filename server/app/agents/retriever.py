"""Retriever Agent

Thin wrapper around the project's `chroma_client` and `embedder` to perform
semantic retrieval. Returns top-K documents with metadata and distances.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from app import chroma_client
from app.agents.embedder import Embedder


class Retriever:
    def __init__(self, collection=None, embed_model: Optional[str] = None):
        self.embed_model = embed_model
        if collection is None:
            client = chroma_client.ChromaClient()
            self.collection = client.get_collection()
        else:
            self.collection = collection

    def retrieve(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        e = Embedder(model_name=self.embed_model)
        qv = e.embed_texts([query])[0]
        try:
            res = self.collection.query(query_embeddings=[qv], n_results=top_k, include=["documents", "metadatas", "distances"])
            return res
        except Exception:
            # fallback to chroma_client.query_similar style
            return chroma_client.query_similar(self.collection, query, top_k)


def retrieve(query: str, top_k: int = 5, collection=None, embed_model: Optional[str] = None) -> Dict[str, Any]:
    r = Retriever(collection=collection, embed_model=embed_model)
    return r.retrieve(query, top_k=top_k)
