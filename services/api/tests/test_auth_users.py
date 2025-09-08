from pathlib import Path
import os
from fastapi.testclient import TestClient
from services.api.app import app as base_app  # or import your factory if you have one

def _setup_app(tmp_path: Path):
    os.environ["PYTEST_CURRENT_TEST"] = "1"
    os.environ["AUTH_MODE"] = "token"
    os.environ["AUTH_SECRET"] = "test-secret"
    os.environ["AUTH_USERS_FILE"] = str(tmp_path / "users.json")
    # also point repo root / state dir to tmp
    os.environ["APP_STATE_DIR"] = str(tmp_path)
    return base_app

def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 409)
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]

def test_register_login_and_me(tmp_path: Path):
    app = _setup_app(tmp_path)
    client = TestClient(app)
    token = _login(client, "alice@example.com", "secret123")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == "alice@example.com"
    assert me["id"].startswith("u_")

def test_plans_are_scoped_by_owner(tmp_path: Path):
    app = _setup_app(tmp_path)
    client = TestClient(app)

    alice = _login(client, "alice@example.com", "a")
    bob = _login(client, "bob@example.com", "b")

    # Alice creates a plan
    r = client.post("/requests", json={"text": "Alice plan"}, headers={"Authorization": f"Bearer {alice}"})
    assert r.status_code == 200
    a_plan = r.json()["plan_id"]

    # Bob creates a plan
    r = client.post("/requests", json={"text": "Bob plan"}, headers={"Authorization": f"Bearer {bob}"})
    assert r.status_code == 200
    b_plan = r.json()["plan_id"]

    # Alice sees only her plan
    r = client.get("/plans", headers={"Authorization": f"Bearer {alice}"})
    assert r.status_code == 200
    j = r.json()
    assert all(p["owner"] != "public" for p in j["plans"])
    assert any(p["id"] == a_plan for p in j["plans"])
    assert all(p["id"] != b_plan for p in j["plans"])

    # Bob sees only his plan
    r = client.get("/plans", headers={"Authorization": f"Bearer {bob}"})
    j = r.json()
    assert any(p["id"] == b_plan for p in j["plans"])
    assert all(p["id"] != a_plan for p in j["plans"])

def test_auth_disabled_is_backwards_compatible(tmp_path: Path, monkeypatch):
    # Disable auth to mirror legacy behavior
    monkeypatch.delenv("AUTH_MODE", raising=False)
    monkeypatch.delenv("AUTH_SECRET", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))

    from services.api.app import app  # import after env set
    client = TestClient(app)

    r = client.post("/requests", json={"text": "Public plan"})
    assert r.status_code == 200
    pid = r.json()["plan_id"]

    r = client.get("/plans")
    assert r.status_code == 200
    j = r.json()
    assert any(p["id"] == pid and p.get("owner") in (None, "public", "public") for p in j["plans"])
