import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_job_invalid_missing_inputs():
    # No required fields provided
    response = client.post('/api/v1/broll/jobs', json={})
    assert response.status_code == 422

def test_job_valid_script_only():
    payload = {"script": "Hello world"}
    response = client.post('/api/v1/broll/jobs', json=payload)
    assert response.status_code == 202
    assert "job_id" in response.json()
