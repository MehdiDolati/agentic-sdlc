from fastapi.testclient import TestClient
from services.api.app import app

client = TestClient(app)

def test_pages_render_and_auth_workflow(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setenv("AUTH_MODE", "on")

    # Register
    r = client.post("/auth/register", json={"email": "me@test.com", "password": "pw"})
    assert r.status_code == 200

    # Login
    r = client.post("/auth/login", json={"email": "me@test.com", "password": "pw"})
    assert r.status_code == 200
    cookie = r.cookies.get("session")
    assert cookie

    # Access /ui root
    client.cookies.set("session", cookie)
    r = client.get("/ui")
    assert r.status_code == 200
    assert "me@test.com" in r.text

    # Check that /ui/plans is rendered
    client.cookies.set("session", cookie)
    r = client.get("/ui/plans")
    assert r.status_code == 200
    assert "<h1" in r.text
