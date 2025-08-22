from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_create_request_returns_plan_id_and_artifacts():
    r = client.post("/requests", json={"text": "Build a notes service with auth"})
    assert r.status_code == 200
    data = r.json()
    assert "plan_id" in data
    assert "artifacts" in data
    assert all(k in data["artifacts"] for k in ("prd","adr","stories","tasks","openapi"))
    pid = data["plan_id"]
    r2 = client.get(f"/plans/{pid}")
    assert r2.status_code == 200
    plan = r2.json()
    assert plan["id"] == pid
    assert "request" in plan and "artifacts" in plan

def test_list_plans():
    r = client.get("/plans")
    assert r.status_code == 200
    j = r.json()
    assert "plans" in j
    assert isinstance(j["plans"], list)
