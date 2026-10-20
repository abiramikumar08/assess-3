"""Legacy job submission/status tests."""
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


class MockJob:
    def __init__(self, job_id, state="queued", result=None):
        self._id = job_id
        self.is_queued   = state == "queued"
        self.is_started  = state == "started"
        self.is_finished = state == "finished"
        self.is_failed   = state == "failed"
        self.result = result
        self.exc_info = None
    def get_id(self): return self._id


def test_job_submission_success(client):
    mock_job = MockJob("mock123")
    with patch("app.api.queue") as mq:
        mq.enqueue.return_value = mock_job
        resp = client.post("/api/v1/broll/jobs", json={"script": "Hello"})
    assert resp.status_code == 202
    data = resp.json()
    assert data["job_id"] == "mock123"
    assert data["status"] == "queued"


def test_job_status_queued(client):
    mock_job = MockJob("mock123", state="queued")
    with patch("rq.job.Job.fetch", return_value=mock_job):
        resp = client.get("/api/v1/broll/jobs/mock123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["result"] is None


def test_job_status_completed(client):
    mock_job = MockJob("mock123", state="finished",
                       result={"video_url": "http://example.com/video.mp4"})
    with patch("rq.job.Job.fetch", return_value=mock_job):
        resp = client.get("/api/v1/broll/jobs/mock123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["result"] == {"video_url": "http://example.com/video.mp4"}


def test_job_status_not_found(client):
    with patch("rq.job.Job.fetch", side_effect=Exception("Not found")):
        resp = client.get("/api/v1/broll/jobs/unknown")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "JOB_NOT_FOUND"
