from pathlib import Path
from fastapi.testclient import TestClient
import importlib

TEMPLATES = [
    ("layout.html",       "<title>Agentic SDLC</title>"),
    ("plans_list.html",   "<h1>Plans</h1>"),
    ("plan_detail.html",  "<h1>Plan</h1>"),
]

def _templates_dir() -> Path:
    # Locate templates next to app.py: services/api/templates
    here = Path(__file__).resolve()
    svc_root = here.parents[2]  # services/api
    return svc_root / "templates"

def test_template_files_exist_and_have_markers():
    tdir = _templates_dir()
    assert tdir.exists(), f"Templates dir not found: {tdir}"

    missing = []
    for filename, marker in TEMPLATES:
        p = tdir / filename
        if not p.exists():
            missing.append(filename)
            continue
        txt = p.read_text(encoding="utf-8")
        assert marker in txt, f"Missing invariant marker in {filename}: {marker}"

    assert not missing, f"Missing template files: {missing}"

def _setup_app(tmp_path: Path):
    import services.api.app as app_module
    importlib.reload(app_module)
    # force isolated repo-root
    app_module._repo_root = lambda: tmp_path  # type: ignore
    return app_module.app, app_module

def _mk_plan(client, text: str):
    r = client.post("/requests", json={"text": text})
    assert r.status_code == 200
    return r.json()

def test_rendered_html_has_invariant_headers(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    app, _ = _setup_app(tmp_path)
    client = TestClient(app)

    # seed one plan
    j = _mk_plan(client, "Snapshot smoke for UI")
    plan_id = j["plan_id"]

    # list page
    r = client.get("/ui/plans")
    assert r.status_code == 200
    body = r.text
    # Stable, human-visible headers and counters
    assert "<h1>Plans</h1>" in body
    assert "Total:" in body

    # detail page
    r = client.get(f"/ui/plans/{plan_id}")
    assert r.status_code == 200
    body = r.text
    assert "<h1>Plan</h1>" in body
    # Sections expected in the MVP
    assert "<h2>PRD</h2>" in body
    assert "<h2>OpenAPI</h2>" in body
