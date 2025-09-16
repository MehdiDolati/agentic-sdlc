from pathlib import Path
import time
from fastapi.testclient import TestClient

from services.api.app import app
from services.api.core.shared import _create_engine, _database_url, _new_id
from services.api.core.repos import PlansRepoDB
from services.api.planner.core import plan_request

client = TestClient(app)

def _seed_plan(tmp_path: Path, vision: str) -> dict:
    planned = plan_request(vision, tmp_path, owner="ui")
    plan_id = _new_id("plan")
    engine = _create_engine(_database_url(tmp_path))
    PlansRepoDB(engine).create({
        "id": plan_id,
        "request": planned.get("request", vision),
        "owner": "ui",
        "artifacts": planned.get("artifacts", {}),
        "status": "new",
    })
    return {"id": plan_id}

def test_runs_list_and_detail(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    p = _seed_plan(tmp_path, "Run mgmt")
    plan_id = p["id"]

    # enqueue a run via UI (returns section HTML)
    r = client.post(f"/ui/plans/{plan_id}/execute")
    assert r.status_code == 200
    assert "Run" in r.text
    run_id = r.text.split("Run ID:")[1].split("<")[0].strip()

    # list page
    r2 = client.get(f"/ui/plans/{plan_id}/runs")
    assert r2.status_code == 200
    assert "Runs" in r2.text

    # table partial should include the run id
    r3 = client.get(f"/ui/plans/{plan_id}/runs/table")
    assert r3.status_code == 200
    assert run_id in r3.text

    # detail page renders and the fragment endpoint returns 200
    r4 = client.get(f"/ui/runs/{run_id}")
    assert r4.status_code == 200
    r5 = client.get(f"/ui/runs/{run_id}/fragment")
    assert r5.status_code == 200
    assert "Logs" in r5.text
    assert "Manifest" in r5.text
