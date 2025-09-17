from pathlib import Path
from fastapi.testclient import TestClient

from services.api.app import app
from services.api.core.shared import _create_engine, _database_url, _new_id
from services.api.core.repos import PlansRepoDB

client = TestClient(app)

def _seed_plan(tmp_path: Path) -> str:
    pid = _new_id("plan")
    eng = _create_engine(_database_url(tmp_path))
    prd_rel = f"docs/prd/PRD-{pid}.md"
    (tmp_path / prd_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / prd_rel).write_text("# PRD\n\nBody", encoding="utf-8")
    PlansRepoDB(eng).create({"id": pid, "request": "GH test", "owner": "ui", "artifacts": {"prd": prd_rel}, "status": "new"})
    return pid

class _FakeGH:
    def __init__(self, token, repo): pass
    def create_issue(self, title, body="", labels=None): return {"number": 123, "html_url": "https://x/issues/123"}
    def ensure_branch(self, base, new_branch): return {"ref": f"refs/heads/{new_branch}"}
    def upsert_files(self, branch, files, message): return {"commit": "abc123"}
    def open_pr(self, head, base, title, body=""): return {"html_url": "https://x/pull/1"}

def test_bulk_issues_and_pr(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    # Configure GH via settings env overrides
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPO", "o/r")
    monkeypatch.setenv("GITHUB_DEFAULT_BRANCH", "main")

    # Patch client
    import services.api.ui.plans as ui_plans
    import services.api.integrations.github as ghmod
    monkeypatch.setattr(ghmod, "GH", _FakeGH)

    pid = _seed_plan(tmp_path)

    # Add a tasks file with one open item
    tasks_rel = f"docs/tasks/{pid}.md"
    (tmp_path / tasks_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / tasks_rel).write_text("- [ ] Do something\n", encoding="utf-8")
    eng = ui_plans._create_engine(ui_plans._database_url(tmp_path))
    repo = ui_plans.PlansRepoDB(eng)
    row = repo.get(pid); arts = (row.get("artifacts") or {}).copy()
    arts["tasks"] = tasks_rel; repo.update_artifacts(pid, arts)

    # Bulk create issues (HTMX)
    r = client.post(f"/ui/plans/{pid}/board/bulk_issues", data={"kind":"tasks","only_open":"on"}, headers={"HX-Request":"true"})
    assert r.status_code == 200
    assert 'id="flash"' in r.text
    assert "Created 1 issues" in r.text

    # Create/Update branch (HTMX)
    r2 = client.post(f"/ui/plans/{pid}/git/branch", data={"branch": f"feature/{pid}"}, headers={"HX-Request":"true"})
    assert r2.status_code == 200
    assert 'id="flash"' in r2.text
    assert "Branch updated" in r2.text

    # Open PR
    r3 = client.post(f"/ui/plans/{pid}/git/pr", data={"branch": f"feature/{pid}", "title": "My PR"}, headers={"HX-Request":"true"})
    assert r3.status_code == 200
    assert 'id="flash"' in r3.text
    assert "PR opened" in r3.text