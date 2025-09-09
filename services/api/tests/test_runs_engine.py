from pathlib import Path
import time
from fastapi.testclient import TestClient

def _setup_app(tmp_path: Path):
    import importlib
    import services.api.app as app_module
    importlib.reload(app_module)
    app_module.app.state.repo_root = str(tmp_path)
    return app_module.app, app_module

def _mk_plan(client: TestClient, text: str) -> dict:
    r = client.post("/requests", json={"text": text})
    r.raise_for_status()
    return r.json()

def test_run_lifecycle_done(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    app, app_module = _setup_app(tmp_path)
    client = TestClient(app)

    plan = _mk_plan(client, "Run lifecycle happy path")
    plan_id = plan["plan_id"]

    # enqueue
    r = client.post(f"/plans/{plan_id}/runs")
    assert r.status_code == 201
    run = r.json()
    run_id = run["id"]
    assert run["status"] == "queued"

    # poll quickly until done (worker uses tiny sleeps under PYTEST_CURRENT_TEST)
    for _ in range(200):
        r = client.get(f"/plans/{plan_id}/runs/{run_id}")
        r.raise_for_status()
        st = r.json()["status"]
        if st in {"done", "failed", "cancelled"}:
            break
        time.sleep(0.01)
    assert st == "done"

    # list endpoint shows it
    r = client.get(f"/plans/{plan_id}/runs")
    r.raise_for_status()
    runs = r.json()
    assert any(x["id"] == run_id and x["status"] == "done" for x in runs)

    # manifest & log exist
    r = client.get(f"/plans/{plan_id}/runs/{run_id}")
    j = r.json()
    assert (tmp_path / (j["manifest_path"] or "")).exists()
    assert (tmp_path / (j["log_path"] or "")).exists()

def test_run_cancel(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    app, app_module = _setup_app(tmp_path)
    client = TestClient(app)

    plan = _mk_plan(client, "Run cancel")
    plan_id = plan["plan_id"]

    r = client.post(f"/plans/{plan_id}/runs")
    r.raise_for_status()
    run_id = r.json()["id"]

    # immediately cancel
    r = client.post(f"/plans/{plan_id}/runs/{run_id}/cancel")
    r.raise_for_status()

    # poll until cancelled
    for _ in range(200):
        r = client.get(f"/plans/{plan_id}/runs/{run_id}")
        st = r.json()["status"]
        if st in {"cancelled", "done", "failed"}:
            break
        time.sleep(0.01)
    assert st == "cancelled"
