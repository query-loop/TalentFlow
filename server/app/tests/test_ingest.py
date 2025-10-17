import pytest

from app import ingest, chroma_client


def test_chunk_text_empty():
    assert ingest.chunk_text("") == []


def test_chunk_text_basic():
    txt = "".join([f"word{i} " for i in range(500)])
    chunks = ingest.chunk_text(txt, chunk_size=100, overlap=10)
    # Expect >0 chunks and overlap behavior
    assert len(chunks) > 0
    # Ensure consecutive chunks overlap by checking that last word of first chunk appears in second chunk
    if len(chunks) >= 2:
        first = chunks[0]["text"].split()
        second = chunks[1]["text"].split()
        assert first[-1] in second


def test_ingest_candidate_calls_upsert(monkeypatch):
    called = {"upsert": False}

    class DummyCollection:
        def upsert(self, ids, metadatas, documents, embeddings=None):
            called["upsert"] = True
            # basic sanity checks
            assert len(ids) == len(documents) == len(metadatas)

    dummy = DummyCollection()

    txt = "This is a test document with enough words " * 10
    n = ingest.ingest_candidate("cand-123", txt, metadata={"source": "unit-test"}, collection=dummy)
    assert n > 0
    assert called["upsert"] is True
