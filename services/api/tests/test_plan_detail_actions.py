# services/api/tests/test_plan_detail_actions.py
import time
from pathlib import Path
from fastapi.testclient import TestClient

from services.api.app import app
from services.api.planner.core import plan_request
from services.api.core.shared import _create_engine, _database_url
from services.api.core.repos import PlansRepoDB
from services.api.core.shared import _new_id

client = TestClient(app)

def _seed_plan(tmp_path: Path, vision: str = "Test plan") -> dict:
    """
    Generate artifacts to disk via planner, then persist a Plan row to the DB.
    plan_request(...) returns artifacts & request text, but not an id; we create one.
    """
    import os
    # Ensure LLM environment is set for plan_request
    os.environ["LLM_PROVIDER"] = "mock"
    os.environ["PYTEST_CURRENT_TEST"] = "1"
    
    # 1) Generate artifacts deterministically under tmp_path/docs/...
    planned = plan_request(vision, tmp_path, owner="ui")
    artifacts = planned.get("artifacts", {})
    request_text = planned.get("request", vision)

    # 2) Persist plan with a fresh id
    plan_id = _new_id("plan")
    engine = _create_engine(_database_url(tmp_path))
    plan_row = {
        "id": plan_id,
        "request": request_text,
        "owner": "ui",
        "artifacts": artifacts,
        "status": "new",
    }
    PlansRepoDB(engine).create(plan_row)

    # 3) Return what the rest of the test expects
    plan_row.update(planned)  # so callers still see artifacts/request/etc.
    return plan_row

def test_execute_run_and_update(monkeypatch, tmp_path):
    # ensure worker runs quickly
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    plan = _seed_plan(tmp_path, "Run test")
    plan_id = plan["id"]
    # Fire execute
    r = client.post(f"/ui/plans/{plan_id}/execute")
    assert r.status_code == 200
    assert "Run" in r.text  # section_run rendered
    # Extract run ID from the HTML via status text
    run_id = r.text.split("Run ID:")[1].split("<")[0].strip()
    # Wait briefly then poll run section
    time.sleep(0.1)
    r2 = client.get(f"/ui/plans/{plan_id}/run/{run_id}")
    assert r2.status_code == 200
    assert "Status" in r2.text

def test_edit_and_download_prd(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    plan = _seed_plan(tmp_path, "Edit tasks")
    plan_id = plan["id"]
    # Ensure the plan has a tasks artifact on disk and in DB
    engine = _create_engine(_database_url(tmp_path))
    repo = PlansRepoDB(engine)
    row = repo.get(plan_id)
    artifacts = (row.get("artifacts") or {}).copy()
    if "tasks" not in artifacts:
        tasks_rel = f"docs/tasks/{plan_id}.md"
        tasks_path = tmp_path / tasks_rel
        tasks_path.parent.mkdir(parents=True, exist_ok=True)
        tasks_path.write_text("# Tasks\n\n- seed item\n", encoding="utf-8")
        artifacts["tasks"] = tasks_rel
        repo.update(plan_id, {"artifacts": artifacts})
    
    # Load edit form
    r = client.get(f"/ui/plans/{plan_id}/artifacts/prd/edit")
    assert r.status_code == 200
    assert "<textarea" in r.text
    # Post updated tasks
    new_content = "# PRD\n\nUpdated content\n"
    r2 = client.post(f"/ui/plans/{plan_id}/artifacts/prd/edit", data={"content": new_content})
    assert r2.status_code == 200
    assert "Updated content" in r2.text
    # Download
    r3 = client.get(f"/plans/{{plan_id}}/artifacts/prd/download".format(plan_id=plan_id))
    assert r3.status_code == 200
    assert new_content.strip().splitlines()[0] in r3.content.decode()
