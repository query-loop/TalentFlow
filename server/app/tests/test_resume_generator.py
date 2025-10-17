from app.agents.resume_generator import generate_resume
from app.chroma_client import ChromaClient


def test_resume_generator_template():
    # create fake collection and upsert a sample experience chunk
    c = ChromaClient(collection_name="rg_test").get_collection()
    c.upsert(ids=["e1"], metadatas=[{"source":"import"}], documents=["Built a search engine that reduced latency by 30%"], embeddings=[[0.1]*8])

    profile = {
        "name": "Jane Candidate",
        "summary": "Senior engineer experienced in search systems.",
        "skills": ["Python", "Search"],
        "education": ["B.S. Computer Science"]
    }

    out = generate_resume(profile, query=None, top_k=1, embed_model=None, llm=None, collection=c)
    assert "# Jane Candidate" in out
    assert "## Experience" in out or "Built a search engine" in out
    assert "## Skills" in out
