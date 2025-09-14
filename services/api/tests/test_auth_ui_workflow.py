# services/api/tests/test_auth_ui_workflow.py
from pathlib import Path
from fastapi.testclient import TestClient
from services.api.app import app as base_app

def _setup_app(tmp_path: Path):
    app = base_app
    app.state.repo_root = str(tmp_path)  # isolate writes
    return app

def test_register_login_me_and_gates(tmp_path: Path, monkeypatch):
    # make app think it's under test (helps deterministic code paths)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    # turn ON auth for this test; other tests remain unauthenticated-by-default
    monkeypatch.setenv("AUTH_MODE", "on")
    
    app = _setup_app(tmp_path)
    client = TestClient(app)

    # 1) Cannot create plan when unauthenticated
    r = client.post("/requests", json={"text": "Blocked unauth plan"})
    assert r.status_code == 401

    # 2) Register -> Login
    r = client.post("/auth/register", json={"email": "u1@example.com", "password": "p1"})
    assert r.status_code == 200
    r = client.post("/auth/login", json={"email": "u1@example.com", "password": "p1"})
    assert r.status_code == 200
    j = r.json()
    assert j.get("access_token")
    # cookie set by server, client stores it automatically

    # 3) /auth/me shows the user
    r = client.get("/auth/me")
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == "u1@example.com"
    assert me["id"].startswith("u_")

    # 4) Now we can create a plan
    r = client.post("/requests", json={"text": "Create a plan"})
    assert r.status_code == 200
    plan = r.json()
    assert plan.get("plan_id")
    assert "prd" in plan.get("artifacts", {})

    # 5) And we can enqueue a run
    pid = plan["plan_id"]
    r = client.post(f"/plans/{pid}/runs")
    assert r.status_code == 201
    run = r.json()
    assert run["id"]

    # 6) Logout and gates apply again
    r = client.post("/ui/logout", follow_redirects=False)
    assert r.status_code in (302, 303)
    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["id"] == "public"
    r = client.post("/requests", json={"text": "Blocked again"})
    assert r.status_code == 401
