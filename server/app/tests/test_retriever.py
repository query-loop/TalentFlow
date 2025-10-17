from app.agents.retriever import retrieve
from app.chroma_client import ChromaClient


def test_retriever_basic():
    # ensure we use the fake collection
    c = ChromaClient(collection_name="test_retriever").get_collection()
    # upsert some docs
    c.upsert(ids=["a"], metadatas=[{"source": "t1"}], documents=["hello world"], embeddings=[[0.1]*8])
    c.upsert(ids=["b"], metadatas=[{"source": "t2"}], documents=["goodbye world"], embeddings=[[0.2]*8])

    res = retrieve("hello", top_k=1, collection=c, embed_model=None)
    assert "documents" in res
    assert len(res["documents"][0]) >= 1
