"""Fetcher utilities for retrieving resume/JD content from various references.

Supported schemes:
- file://path/to/file.txt
- http(s)://... (requires `requests` installed, otherwise will raise)
- minio://bucket/object (uses `app.storage` client to download)

Returns decoded text (utf-8) or raises on failure.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse
import os
import io
import requests

from app import storage

# Local imports for parsing
from pypdf import PdfReader
import docx


def _extract_text_from_pdf_bytes(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        texts = []
        for p in reader.pages:
            try:
                texts.append(p.extract_text() or "")
            except Exception:
                # ignore page-level extraction errors
                texts.append("")
        return "\n".join(texts)
    except Exception:
        return ""


def _extract_text_from_docx_bytes(data: bytes) -> str:
    try:
        bio = io.BytesIO(data)
        doc = docx.Document(bio)
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(paragraphs)
    except Exception:
        return ""


def _extract_text_from_bytes(data: bytes, filename: Optional[str] = None, content_type: Optional[str] = None) -> str:
    """Try to detect and extract text from bytes for common document types (pdf, docx, txt).

    filename/content_type are hints to prefer a parser.
    """
    # prefer filename extension
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".pdf":
            return _extract_text_from_pdf_bytes(data)
        if ext in (".docx", ".doc"):
            return _extract_text_from_docx_bytes(data)

    # check content type
    if content_type:
        if "pdf" in content_type:
            return _extract_text_from_pdf_bytes(data)
        if "officedocument" in content_type or "msword" in content_type or "word" in content_type:
            return _extract_text_from_docx_bytes(data)

    # fallback heuristics: try text decode, then pdf/docx
    try:
        text = data.decode("utf-8")
        # if decoding successful and contains many printable chars, return
        if len(text.strip()) > 0:
            return text
    except Exception:
        pass

    # try pdf
    txt = _extract_text_from_pdf_bytes(data)
    if txt:
        return txt

    # try docx
    txt = _extract_text_from_docx_bytes(data)
    if txt:
        return txt

    return ""


def extract_text_from_bytes(data: bytes, filename: Optional[str] = None, content_type: Optional[str] = None) -> str:
    """Public helper: wrapper around binary extraction heuristics."""
    return _extract_text_from_bytes(data, filename=filename, content_type=content_type)


def fetch_text(ref: str, minio_client: Optional[object] = None, filename_hint: Optional[str] = None) -> str:
    p = urlparse(ref)
    scheme = p.scheme
    # file path or local path
    if scheme in ("file", ""):
        path = p.path or ref
        with open(path, "rb") as f:
            data = f.read()
        return _extract_text_from_bytes(data, filename=os.path.basename(path))

    if scheme in ("http", "https"):
        try:
            resp = requests.get(ref, timeout=20)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            data = resp.content
            # prefer text response
            if content_type.startswith("text/"):
                try:
                    return data.decode("utf-8", errors="ignore")
                except Exception:
                    pass
            return _extract_text_from_bytes(data, filename_hint, content_type)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch URL {ref}: {e}")

    if scheme == "minio":
        # ref like minio://bucket/object/path
        bucket = p.netloc
        obj = p.path.lstrip("/")
        client = minio_client or storage.get_client()
        data = storage.download_bytes(obj, client=client, bucket=bucket)
        if data is None:
            raise RuntimeError(f"MinIO object not found: {ref}")
        return _extract_text_from_bytes(data, os.path.basename(obj))

    raise RuntimeError(f"Unsupported scheme in ref: {ref}")
