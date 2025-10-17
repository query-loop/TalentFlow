import tempfile
import os
from app.utils.fetcher import fetch_text
from app.ingest import ingest_from_reference
from app.chroma_client import ChromaClient


def test_fetch_file_and_ingest():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        tf.write("Line one\nLine two with Python and AWS")
        tf.flush()
        path = tf.name

    try:
        txt = fetch_text(f"file://{path}")
        assert "Line one" in txt

        c = ChromaClient(collection_name="fetch_test").get_collection()
        count = ingest_from_reference("cand_file", f"file://{path}", metadata={"src":"test"}, collection=c)
        assert count > 0
    finally:
        os.unlink(path)
