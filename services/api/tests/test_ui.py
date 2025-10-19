from pathlib import Path
from fastapi.testclient import TestClient
import importlib
import json

def _setup_app(tmp_path: Path):
    import services.api.app as app_module
    importlib.reload(app_module)
    def _fake_repo_root():
        return tmp_path
    app_module._repo_root = _fake_repo_root  # type: ignore
    return app_module.app, app_module

def _mk_plan(client, text: str):
    r = client.post("/requests", json={"text": text})
    assert r.status_code == 200
    return r.json()

def test_ui_plans_list_renders_and_filters(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    app, app_module = _setup_app(tmp_path)
    client = TestClient(app)

    _mk_plan(client, "Create a hello endpoint")
    _mk_plan(client, "Build a notes service with auth")

    # Root should redirect to /ui/plans
    r = client.get("/", follow_redirects=True)
    assert r.status_code == 200
    assert "<h1>Plans</h1>" in r.text

    # Server-rendered list exists
    r = client.get("/ui/plans")
    assert r.status_code == 200
    assert "<h1>Plans</h1>" in r.text
    assert "Total:" in r.text

    # Search via query param
    r = client.get("/ui/plans?q=hello")
    assert r.status_code == 200
    assert "hello endpoint" in r.text

def test_ui_plan_detail_and_sections(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    app, app_module = _setup_app(tmp_path)
    client = TestClient(app)

    j = _mk_plan(client, "Add search to notes list")
    plan_id = j["plan_id"]

    # Plan detail renders
    r = client.get(f"/ui/plans/{plan_id}")
    assert r.status_code == 200
    assert "Add search to notes list" in r.text
    # PRD section should be present by default
    assert "<h2>PRD</h2>" in r.text

    # HTMX partials render just the section fragment
    r = client.get(f"/ui/plans/{plan_id}/sections/prd", headers={"HX-Request": "true"})
    assert r.status_code == 200
    assert r.text.strip().startswith("<div class=\"card\">")
    assert "<h2>PRD</h2>" in r.text

    r = client.get(f"/ui/plans/{plan_id}/sections/openapi", headers={"HX-Request": "true"})
    assert r.status_code == 200
    assert "<h2>OpenAPI</h2>" in r.text
    assert "openapi:" in r.text

def test_ui_plan_detail_404(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    app, _ = _setup_app(tmp_path)
    client = TestClient(app)

    r = client.get("/ui/plans/does-not-exist")
    assert r.status_code == 404
