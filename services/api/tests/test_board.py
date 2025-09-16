from pathlib import Path
from fastapi.testclient import TestClient

from services.api.app import app
from services.api.core.shared import _create_engine, _database_url, _new_id
from services.api.core.repos import PlansRepoDB

client = TestClient(app)

def _seed_plan_with_lists(tmp_path: Path, vision="Board test"):
    # create a bare plan row with tasks & stories files
    plan_id = _new_id("plan")
    engine = _create_engine(_database_url(tmp_path))
    tasks_rel = f"docs/tasks/{plan_id}.md"
    stories_rel = f"docs/stories/{plan_id}.md"
    (tmp_path / tasks_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / stories_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / tasks_rel).write_text("## backlog\n- [ ] task A\n- [x] task B\n", encoding="utf-8")
    (tmp_path / stories_rel).write_text("- [ ] story 1\n", encoding="utf-8")
    PlansRepoDB(engine).create({
        "id": plan_id, "request": vision, "owner": "ui",
        "artifacts": {"tasks": tasks_rel, "stories": stories_rel},
        "status": "new",
    })
    return plan_id

def test_board_list_toggle(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    plan_id = _seed_plan_with_lists(tmp_path)

    # page + data
    r = client.get(f"/ui/plans/{plan_id}/board")
    assert r.status_code == 200
    r2 = client.get(f"/ui/plans/{plan_id}/board/data")
    assert r2.status_code == 200
    assert "Tasks" in r2.text
    assert "Stories" in r2.text

    # toggle first task from [ ] -> [x]
    r3 = client.post(f"/ui/plans/{plan_id}/board/toggle", data={"kind": "tasks", "index": 0, "done": True})
    assert r3.status_code == 200

    # verify file updated
    tasks_rel = f"docs/tasks/{plan_id}.md"
    new_text = (tmp_path / tasks_rel).read_text(encoding="utf-8")
    assert "- [x] task A" in new_text
