from fastapi.testclient import TestClient
from app.main import app
import importlib

client = TestClient(app)


def test_models_list():
    resp = client.get("/api/agents/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    assert "embedder" in data["models"]


def test_models_load_fallback():
    # If transformers isn't installed the endpoint should return fallback message
    resp = client.post("/api/agents/models/load", json={"model_id": "sentence-transformers/all-MiniLM-L6-v2"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["fallback", "loaded", "error"]


def test_generate_with_model_id():
    # Call generate endpoint with a model_id. In dev environment it should still return a resume string.
    profile = {"name": "Test Candidate", "summary": "Experienced developer", "skills": ["Python", "SQL"]}
    resp = client.post("/api/agents/generate", json={"profile": profile, "model_id": "deepseek/DeepSeek-R1-0528"})
    assert resp.status_code == 200
    data = resp.json()
    assert "resume" in data


def test_azure_github_load_fallback():
    # Try loading the GitHub model path; without GITHUB_TOKEN this should return a fallback status
    resp = client.post("/api/agents/models/load", json={"model_id": "deepseek/DeepSeek-R1-0528"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in ["fallback", "error", "loaded"]
