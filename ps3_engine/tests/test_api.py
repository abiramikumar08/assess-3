"""Legacy API and job tests — kept for regression coverage."""
import os
os.environ.setdefault("TTS_PROVIDER", "mock")
os.environ.setdefault("FOOTAGE_PROVIDER", "mock")

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


class _MockJob:
    def __init__(self, jid="mock123", state="queued", result=None):
        self._id = jid
        self.is_queued   = state == "queued"
        self.is_started  = state == "started"
        self.is_finished = state == "finished"
        self.is_failed   = state == "failed"
        self.result = result
        self.exc_info = None
    def get_id(self): return self._id


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


def test_job_invalid_missing_inputs(client):
    r = client.post("/api/v1/broll/jobs", json={})
    assert r.status_code == 422


def test_job_valid_script_only(client):
    mock_job = _MockJob()
    with patch("app.api.queue") as mq:
        mq.enqueue.return_value = mock_job
        r = client.post("/api/v1/broll/jobs", json={"script": "Hello world"})
    assert r.status_code == 202
    assert "job_id" in r.json()
