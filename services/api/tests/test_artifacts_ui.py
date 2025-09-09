from __future__ import annotations
from pathlib import Path
from fastapi.testclient import TestClient
import importlib

def _setup_app(tmp_path: Path):
    import services.api.app as app_module
    importlib.reload(app_module)
    app_module.app.state.repo_root = str(tmp_path)
    return app_module.app, app_module

def _mk_plan(client: TestClient, text: str) -> dict:
    r = client.post("/requests", json={"text": text})
    r.raise_for_status()
    return r.json()

def test_artifact_view_and_diff(tmp_path: Path, monkeypatch):
    # speed worker & deterministic behavior
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    app, app_module = _setup_app(tmp_path)
    client = TestClient(app)

    # Create two plans so we have at least two revisions of each kind
    j1 = _mk_plan(client, "First PRD content")
    j2 = _mk_plan(client, "Second PRD content")
    plan_id = j2["plan_id"]  # use latest plan id for UI scope

    # View PRD
    r = client.get(f"/ui/plans/{plan_id}/artifacts/prd")
    assert r.status_code == 200
    assert "<h2>PRD</h2>" in r.text
    # OpenAPI view
    r = client.get(f"/ui/plans/{plan_id}/artifacts/openapi")
    assert r.status_code == 200
    assert "openapi" in r.text.lower()

    # Explicit diff using artifact paths from two outputs
    prd1 = j1["artifacts"]["prd"]
    prd2 = j2["artifacts"]["prd"]
    r = client.get(f"/ui/plans/{plan_id}/artifacts/prd/diff", params={"frm": prd1, "to": prd2})
    assert r.status_code == 200
    # HtmlDiff tables contain "diff_header" and file names
    assert "Diff" in r.text or "diff" in r.text
    assert prd1 in r.text and prd2 in r.text

    # Auto diff (should pick last two PRD files)
    r = client.get(f"/ui/plans/{plan_id}/artifacts/prd/diff")
    assert r.status_code == 200
    assert "Diff" in r.text or "diff" in r.text
