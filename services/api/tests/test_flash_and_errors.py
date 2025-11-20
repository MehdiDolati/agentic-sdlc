from fastapi.testclient import TestClient
from pathlib import Path
from services.api.app import app
from services.api.tests.test_plan_detail_actions import _seed_plan  # reuse helper

client = TestClient(app)

def test_htmx_404_returns_flash_fragment(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    # Ask for a non-existent plan section via HTMX
    r = client.get("/ui/plans/does-not-exist/sections/prd", headers={"HX-Request": "true"})
    assert r.status_code == 404
    # Should render the flash partial (oob)
    assert 'id="flash"' in r.text
    assert "Plan not found" in r.text or "404" in r.text

def test_board_toggle_out_of_range_shows_flash(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    # Out-of-range index -> 400, and flash fragment for HTMX
    r = client.post(
        "/ui/plans/p123/board/toggle",
        data={"kind": "tasks", "index": 999, "done": True},
        headers={"HX-Request": "true"},
    )
    assert r.status_code in (400, 404)  # depending on whether plan exists; both should flash
    assert 'id="flash"' in r.text

client = TestClient(app)

def test_htmx_500_returns_flash_fragment(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    # Patch a helper used by a UI endpoint to raise
    import services.api.ui.plans as ui_plans
    original = ui_plans.PlansRepoDB.get
    def boom(self, _): raise RuntimeError("kaboom")
    monkeypatch.setattr(ui_plans.PlansRepoDB, "get", boom)
    try:
        r = client.get("/ui/plans/ANY/sections/tasks", headers={"HX-Request": "true"})
        assert r.status_code == 500
        assert 'id="flash"' in r.text
        assert "Error" in r.text or "Unexpected error" in r.text
    finally:
        # restore to be safe for following tests
        monkeypatch.setattr(ui_plans.PlansRepoDB, "get", original)

def test_execute_returns_success_flash(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    p = _seed_plan(tmp_path, "Run flash")
    r = client.post(f"/ui/plans/{p['id']}/execute", headers={"HX-Request": "true"})
    assert r.status_code == 200
    assert 'id="flash"' in r.text
    assert "Run queued" in r.text or "Started" in r.text

def test_artifact_edit_returns_success_flash(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    p = _seed_plan(tmp_path, "Edit PRD flash")
    pid = p["id"]
    # open editor to ensure path is set (not strictly required)
    r0 = client.get(f"/ui/plans/{pid}/artifacts/prd/edit")
    assert r0.status_code == 200
    r = client.post(f"/ui/plans/{pid}/artifacts/prd/edit", data={"content": "# PRD\n\nx"})
    assert r.status_code == 200
    assert 'id="flash"' in r.text
    assert "Saved" in r.text

from services.api.core.shared import _create_engine, _database_url, _new_id
from services.api.core.repos import PlansRepoDB

def _seed_board_plan(tmp_path: Path):
    pid = _new_id("plan")
    eng = _create_engine(_database_url(tmp_path))
    tasks_rel = f"docs/tasks/{pid}.md"
    (tmp_path / tasks_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / tasks_rel).write_text("- [ ] t1\n", encoding="utf-8")
    PlansRepoDB(eng).create({"id": pid, "request": "Board", "owner": "ui",
                             "artifacts": {"tasks": tasks_rel}, "status": "new"})
    return pid

def test_board_toggle_edit_add_flash(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    pid = _seed_board_plan(tmp_path)

    r1 = client.post(f"/ui/plans/{pid}/board/toggle",
                     data={"kind":"tasks","index":0,"done":True},
                     headers={"HX-Request":"true"})
    assert r1.status_code == 200 and 'id="flash"' in r1.text and "Updated" in r1.text

    r2 = client.post(f"/ui/plans/{pid}/board/edit",
                     data={"kind":"tasks","index":0,"title":"t1-mod","section":""},
                     headers={"HX-Request":"true"})
    assert r2.status_code == 200 and 'id="flash"' in r2.text and "Saved" in r2.text

    r3 = client.post(f"/ui/plans/{pid}/board/add",
                     data={"kind":"tasks","title":"t2","section":""},
                     headers={"HX-Request":"true"})
    assert r3.status_code == 200 and 'id="flash"' in r3.text and "Added" in r3.text

def test_board_invalid_index_shows_error_flash(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    pid = _seed_board_plan(tmp_path)
    r = client.post(f"/ui/plans/{pid}/board/toggle",
                    data={"kind":"tasks","index":999,"done":True},
                    headers={"HX-Request":"true"})
    assert r.status_code == 400
    assert 'id="flash"' in r.text

def test_htmx_500_returns_flash_fragment(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))

    import services.api.ui.plans as ui_plans
    original_get = ui_plans.PlansRepoDB.get

    def boom(self, *args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(ui_plans.PlansRepoDB, "get", boom)

    # IMPORTANT: let FastAPI convert exceptions to responses
    client = TestClient(app, raise_server_exceptions=False)

    try:
        r = client.get("/ui/plans/ANY/sections/tasks", headers={"HX-Request": "true"})
        assert r.status_code == 500
        assert 'id="flash"' in r.text
        assert "Error" in r.text or "Unexpected error" in r.text
    finally:
        monkeypatch.setattr(ui_plans.PlansRepoDB, "get", original_get)