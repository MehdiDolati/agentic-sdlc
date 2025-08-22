from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_planner_endpoint_creates_artifacts():
    r = client.post("/requests", json={"text": "Create a hello endpoint"})
    assert r.status_code == 200
    data = r.json()
    assert "artifacts" in data
    artifacts = data["artifacts"]
    assert all(k in artifacts for k in ("prd", "adr", "stories", "tasks", "openapi"))
    for v in artifacts.values():
        assert isinstance(v, str) and len(v) > 0
