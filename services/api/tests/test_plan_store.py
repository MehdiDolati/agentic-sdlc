from pathlib import Path
from services.api.storage import plan_store
import json
import time

def _retarget_store(tmp_path: Path):
    # Redirect the store to a temp file/dir for this test session
    plan_store._DATA_DIR = tmp_path  # type: ignore[attr-defined]
    plan_store._DATA_DIR.mkdir(parents=True, exist_ok=True)
    plan_store._PLAN_FILE = tmp_path / "plan.json"  # type: ignore[attr-defined]

def test_upsert_and_get_plan(tmp_path):
    _retarget_store(tmp_path)

    plan = {
        "goal": "Ship MVP",
        "steps": [
            {"title": "Write PRD"},
            {"title": "Emit OpenAPI", "artifacts": [{"path": "openapi.yaml", "type": "openapi"}]},
        ],
    }
    saved = plan_store.upsert_plan(plan)

    assert saved.get("id")
    assert saved["goal"] == "Ship MVP"
    assert saved.get("created_at") and saved.get("updated_at")
    assert len(saved["steps"]) == 2
    assert saved["steps"][1]["artifacts"][0]["path"] == "openapi.yaml"

    fetched = plan_store.get_plan(saved["id"])
    assert fetched and fetched["id"] == saved["id"]

def test_list_plans_counts_and_sort(tmp_path):
    _retarget_store(tmp_path)

    # Insert two plans, ensure index counts and sorting by updated_at desc
    a = plan_store.upsert_plan({"goal": "A", "steps": [{"title": "s1"}]})
    time.sleep(0.01)  # ensure updated_at differs
    b = plan_store.upsert_plan({"goal": "B", "steps": [{"title": "s1", "artifacts":[{"path":"f.txt"}]}]})

    idx = plan_store.list_plans()
    # newest first
    assert idx[0]["id"] == b["id"]
    assert idx[0]["artifact_count"] == 1
    assert idx[0]["step_count"] == 1
    assert idx[1]["id"] == a["id"]
    assert idx[1]["artifact_count"] == 0
    assert idx[1]["step_count"] == 1

def test_upsert_updates_updated_at(tmp_path):
    _retarget_store(tmp_path)

    p = plan_store.upsert_plan({"goal": "Update Me"})
    first_updated = p["updated_at"]

    # modify and upsert again
    p["goal"] = "Updated"
    again = plan_store.upsert_plan(p)
    assert again["goal"] == "Updated"
    assert again["updated_at"] != first_updated
