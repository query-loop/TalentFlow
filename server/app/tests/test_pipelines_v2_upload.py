import io
import json

from fastapi.testclient import TestClient

from app.main import app


def test_upload_persists_and_enqueues(monkeypatch):
    client = TestClient(app)

    # monkeypatch storage.upload_bytes to return predictable URI
    def fake_upload_bytes(data: bytes, object_name: str, content_type: str = "application/octet-stream", client=None, bucket=None):
        return f"minio://test-bucket/{object_name}"

    monkeypatch.setattr('app.storage.upload_bytes', fake_upload_bytes)

    # monkeypatch parse_resume_task.delay to return object with id
    class DummyAsync:
        def __init__(self, id):
            self.id = id

    def fake_delay(candidate_id, bucket, object_key):
        return DummyAsync('fake-task-123')

    monkeypatch.setattr('app.tasks.parse_resume_task', type('X', (), {'delay': staticmethod(fake_delay)}))

    # create pipeline first
    resp = client.post('/api/pipelines-v2', json={"name": "test","company": "Acme"})
    assert resp.status_code == 201
    pipe = resp.json()

    # upload a resume file
    files = {
        'resume_file': ('resume.txt', io.BytesIO(b'This is a resume text'), 'text/plain')
    }
    res = client.post(f"/api/pipelines-v2/{pipe['id']}/upload", files=files)
    assert res.status_code == 200
    body = res.json()
    # artifacts should include resume minio_uri and parse_job_id
    artifacts = body.get('artifacts') or {}
    resume = artifacts.get('resume') or {}
    assert 'minio_uri' in resume
    assert 'parse_job_id' in resume
    assert resume['parse_job_id'] == 'fake-task-123'
