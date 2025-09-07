from pathlib import Path
from fastapi.testclient import TestClient
import importlib

def _setup_app(tmp_path: Path):
    # Re-import the app so it picks up our monkeypatched repo_root
    import app as app_module
    importlib.reload(app_module)

    def _fake_repo_root():
        return tmp_path
    app_module._repo_root = _fake_repo_root  # type: ignore
    return app_module.app, app_module

def _mk(app_module, client, text: str):
    r = client.post("/requests", json={"text": text})
    assert r.status_code == 200
    return r.json()

def test_plans_fulltext_and_filters(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")  # keep test runs isolated
    app, app_module = _setup_app(tmp_path)
    client = TestClient(app)

    # Seed a few plans
    a = _mk(app_module, client, "Build a notes service with auth")
    b = _mk(app_module, client, "Create a hello endpoint")
    c = _mk(app_module, client, "Add search to notes list")

    # Basic list still returns the legacy shape
    r = client.get("/plans")
    assert r.status_code == 200
    j = r.json()
    assert "plans" in j and isinstance(j["plans"], list)
    assert j["total"] >= 3

    # Full-text search (match on request)
    r = client.get("/plans?q=hello")
    j = r.json()
    assert any("hello endpoint" in p["request"] for p in j["plans"])

    # Full-text search (match on artifacts path)
    # OpenAPI paths always exist and contain 'openapi-'
    r = client.get("/plans?q=openapi-")
    j = r.json()
    assert j["plans"], "expected at least one match on artifact path"

    # Artifact type filter (requires our compatible query param)
    # openapi should match every plan created by /requests
    r = client.get("/plans?artifact_type=openapi")
    j = r.json()
    assert j["plans"] and all("openapi" in p.get("artifacts", {}) for p in j["plans"])

    # Pagination echo (limit/offset)
    r = client.get("/plans?limit=2&offset=0")
    j = r.json()
    assert j["limit"] == 2
    assert j["offset"] == 0
    assert len(j["plans"]) <= 2

    # Sorting works and is stable fields
    r1 = client.get("/plans?sort=created_at&order=asc")
    r2 = client.get("/plans?sort=created_at&order=desc")
    j1, j2 = r1.json(), r2.json()
    assert j1["plans"] and j2["plans"]
    assert j1["plans"][0]["id"] != j2["plans"][0]["id"]
