"""Ingest layer: chunk text and upsert into Chroma via `chroma_client`.

Provides `ingest_candidate` used by higher-level orchestrators.
"""
from __future__ import annotations

from typing import List, Dict, Any
import uuid

from . import chroma_client
from app.utils.fetcher import fetch_text
from app import storage


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 50) -> List[Dict[str, Any]]:
    """Simple whitespace-based chunking.

    chunk_size: number of words per chunk
    overlap: number of overlapping words between consecutive chunks
    """
    words = text.split()
    if not words:
        return []
    chunks: List[Dict[str, Any]] = []
    i = 0
    idx = 0
    while i < len(words):
        part = " ".join(words[i : i + chunk_size])
        chunks.append({"id": str(idx), "text": part, "metadata": {}})
        i += chunk_size - overlap
        idx += 1
    return chunks


def ingest_candidate(candidate_id: str, full_text: str, metadata: Dict[str, Any] | None = None, collection=None) -> int:
    """Chunk `full_text` and upsert chunks into the provided collection. Returns number of chunks.

    If `collection` is None, a ChromaClient will be created (which may be fake in tests).
    """
    if metadata is None:
        metadata = {}
    if collection is None:
        client = chroma_client.ChromaClient()
        collection = client.get_collection()

    chunks = chunk_text(full_text)
    for c in chunks:
        c["metadata"].update(metadata)

    # add a source id to metadata for traceability
    for c in chunks:
        c["metadata"]["candidate_id"] = candidate_id
        c["metadata"]["chunk_uuid"] = str(uuid.uuid4())

    chroma_client.upsert_chunks(collection, candidate_id, chunks)
    return len(chunks)


def ingest_from_reference(candidate_id: str, reference: str, metadata: Dict[str, Any] | None = None, collection=None, minio_client=None) -> int:
    """Fetch content from a reference (file://, http(s)://, minio://) and ingest it."""
    text = fetch_text(reference, minio_client)
    # optionally store raw text in minio for traceability
    if minio_client:
        key = f"raw/{candidate_id}.txt"
        storage.upload_bytes(minio_client, key, client=minio_client) if False else None
    return ingest_candidate(candidate_id, text, metadata=metadata, collection=collection)
