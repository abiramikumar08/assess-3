import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class MockJob:
    def __init__(self, job_id, state='queued', result=None):
        self._id = job_id
        self._state = state
        self.result = result
    def get_id(self):
        return self._id
    @property
    def is_queued(self):
        return self._state == 'queued'
    @property
    def is_started(self):
        return self._state == 'started'
    @property
    def is_finished(self):
        return self._state == 'finished'
    @property
    def is_failed(self):
        return self._state == 'failed'

def test_job_submission_success(monkeypatch):
    mock_job = MockJob('mock123')
    def fake_enqueue(payload):
        return mock_job
    monkeypatch.setattr('app.api.queue.enqueue', fake_enqueue)
    payload = {"script": "Hello"}
    resp = client.post('/api/v1/broll/jobs', json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert data['job_id'] == 'mock123'
    assert data['status'] == 'queued'

def test_job_status_queued(monkeypatch):
    mock_job = MockJob('mock123', state='queued')
    monkeypatch.setattr('rq.job.Job.fetch', lambda job_id, connection=None: mock_job)
    resp = client.get('/api/v1/broll/jobs/mock123')
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'queued'
    assert data['result'] is None

def test_job_status_completed(monkeypatch):
    mock_job = MockJob('mock123', state='finished', result={"video_url": "http://example.com/video.mp4"})
    monkeypatch.setattr('rq.job.Job.fetch', lambda job_id, connection=None: mock_job)
    resp = client.get('/api/v1/broll/jobs/mock123')
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'completed'
    assert data['result'] == {video_url: http://example.com/video.mp4}

def test_job_status_not_found(monkeypatch):
    def raise_err(job_id, connection=None):
        raise Exception('Not found')
    monkeypatch.setattr('rq.job.Job.fetch', raise_err)
    resp = client.get('/api/v1/broll/jobs/unknown')
    assert resp.status_code == 404
    assert resp.json()['detail'] == 'Job not found'
