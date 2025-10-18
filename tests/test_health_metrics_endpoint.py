import os, sys
sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from src.server.app import app

def test_health_metrics_endpoint_ok():
    client = TestClient(app)
    # Auth middleware excludes /health, so no Authorization header needed
    resp = client.get("/health/metrics")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "application_metrics" in data
    assert "system_metrics" in data

