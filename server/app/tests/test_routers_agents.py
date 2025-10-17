from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_parse_text_endpoint():
    resp = client.post("/api/agents/parse", json={"text": "John Doe\nExperience: Worked at ACME Corp as a software engineer."})
    assert resp.status_code == 200
    data = resp.json()
    assert "profile" in data


def test_orchestrate_minimal():
    job = {"title": "Software Engineer", "description": "Develop software"}
    payload = {"candidate_id": "cand-test-1", "resume_text": "Jane Doe\nSkilled in Python and SQL.", "job": job}
    resp = client.post("/api/agents/orchestrate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "resume" in data
    assert "score" in data
