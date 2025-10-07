import pytest
import os
from fastapi.testclient import TestClient
from services.api.app import app
import services.api.core.shared as shared

client = TestClient(app)

@pytest.fixture(autouse=True)
def isolate_repo_root(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    yield
    shared._reset_repo_root_cache_for_tests()

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
