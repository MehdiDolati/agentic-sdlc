from pathlib import Path
from fastapi.testclient import TestClient
from services.api.app import app
from services.api.core.shared import _create_engine, _database_url, _new_id
from services.api.core.repos import PlansRepoDB

client = TestClient(app)

def _seed(tmp_path: Path) -> str:
    pid = _new_id("plan")
    eng = _create_engine(_database_url(tmp_path))
    (tmp_path / f"docs/tasks/{pid}.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"docs/tasks/{pid}.md").write_text("- [ ] item\n", encoding="utf-8")
    PlansRepoDB(eng).create({"id": pid,"request":"board","owner":"ui","artifacts":{"tasks":f"docs/tasks/{pid}.md"},"status":"new"})
    return pid

def test_bulk_issues_success_flash_in_tests(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")  # triggers test-mode short-circuit
    pid = _seed(tmp_path)
    r = client.post(f"/ui/plans/{pid}/board/bulk_issues", data={"kind":"tasks","only_open":"on"}, headers={"HX-Request":"true"})
    assert r.status_code == 200
    assert 'id="flash"' in r.text
    assert "Created 1 issues" in r.text
