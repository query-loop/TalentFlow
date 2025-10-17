from app.agents.embedder import embed_texts


def test_embedder_fallback():
    texts = ["hello world", "another text"]
    emb = embed_texts(texts, model_name=None)
    assert isinstance(emb, list)
    assert len(emb) == 2
    assert all(isinstance(v, list) for v in emb)
    assert all(len(v) == 8 for v in emb)
    # deterministic: calling again yields same result
    emb2 = embed_texts(texts, model_name=None)
    assert emb == emb2
