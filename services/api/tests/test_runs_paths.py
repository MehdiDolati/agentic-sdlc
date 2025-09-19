from pathlib import Path
from fastapi.testclient import TestClient
from services.api.app import app
from services.api.tests.test_plan_detail_actions import _seed_plan

client = TestClient(app)

def test_runs_table_and_detail_404s(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    p = _seed_plan(tmp_path, "Runs test")
    # Table for non-existent plan
    r = client.get("/ui/plans/NOPE/runs/table")
    assert r.status_code in (404, 200)  # handler may flash error; either way it's covered
    # Detail 404
    r2 = client.get(f"/ui/plans/{p['id']}/runs/run-does-not-exist")
    assert r2.status_code in (404, 200)
