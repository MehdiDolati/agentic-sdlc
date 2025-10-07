import pytest
from fastapi.testclient import TestClient
from services.api.app import app

client = TestClient(app)

def test_log_interaction_and_list():
    # Log a new interaction
    payload = {
        "project_id": "test-proj-1",
        "prompt": "What are the requirements?",
        "response": "Here are the requirements...",
        "role": "user",
        "metadata": {"source": "unit-test"}
    }
    resp = client.post("/api/history/", json=payload)
    assert resp.status_code == 201
    assert resp.json()["ok"] is True

    # List all
    resp = client.get("/api/history/")
    assert resp.status_code == 200
    found = [h for h in resp.json() if h["prompt"] == payload["prompt"]]
    assert found, "Logged interaction not found in list_all"

    # List by project
    resp = client.get(f"/api/history/project/{payload['project_id']}")
    assert resp.status_code == 200
    found = [h for h in resp.json() if h["prompt"] == payload["prompt"]]
    assert found, "Logged interaction not found in list_by_project"
