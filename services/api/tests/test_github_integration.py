# services/api/tests/test_github_integration.py
from pathlib import Path
from fastapi.testclient import TestClient

import services.api.integrations.github as ghmod
import services.api.ui.plans as ui_plans
from services.api.app import app
from services.api.core.shared import _repo_root, _create_engine, _database_url, _new_id
from services.api.core.repos import PlansRepoDB


def _seed_plan(tmp_path: Path) -> str:
    """Create a minimal plan in the DB and return its id."""
    pid = _new_id("plan")
    eng = _create_engine(_database_url(tmp_path))
    PlansRepoDB(eng).create({
        "id": pid,
        "request": "GH test",
        "owner": "ui",
        "artifacts": {},
        "status": "new",
    })
    return pid


class _FakeGH:
    def __init__(self, token, repo):
        pass

    def create_issue(self, title, body="", labels=None):
        # simulate a created issue
        return {"number": 123, "html_url": "https://example.test/issues/123"}

    def ensure_branch(self, base, new_branch):
        return {"ref": f"refs/heads/{new_branch}"}

    def upsert_files(self, branch, files, message):
        return {"commit": "deadbeef"}

    def open_pr(self, head, base, title, body=""):
        return {"html_url": "https://example.test/pull/1"}


def test_bulk_issues_and_pr(monkeypatch, tmp_path: Path):
    # --- Environment FIRST ---
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("AUTH_MODE", "off")
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPO", "o/r")
    monkeypatch.setenv("GITHUB_DEFAULT_BRANCH", "main")
    try:
        _repo_root.cache_clear()
    except AttributeError:
        pass

    # --- Auth: force gate off and a non-public user ---
    monkeypatch.setattr(ui_plans, "_auth_enabled", lambda: False, raising=True)
    app.dependency_overrides[ui_plans.get_current_user] = lambda: {"id": "u_test", "email": "t@example.com"}

    # --- Mock GitHub client to avoid network ---
    # IMPORTANT: patch BOTH the symbol used by the route (ui_plans.GH) and the source module (ghmod.GH).
    monkeypatch.setattr(ui_plans, "GH", _FakeGH, raising=True)
    monkeypatch.setattr(ghmod, "GH", _FakeGH, raising=True)

    # --- Create client AFTER env + overrides ---
    client = TestClient(app)

    # --- Seed a plan and attach a tasks file to artifacts ---
    pid = _seed_plan(tmp_path)
    tasks_rel = f"docs/tasks/{pid}.md"
    (tmp_path / tasks_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / tasks_rel).write_text("- [ ] Do something\n", encoding="utf-8")

    eng = _create_engine(_database_url(tmp_path))
    repo = PlansRepoDB(eng)
    row = repo.get(pid)
    arts = (row.get("artifacts") or {}).copy()
    arts["tasks"] = tasks_rel
    # update_artifacts merges/persists
    repo.update_artifacts(pid, arts)

    # --- Bulk create issues (HTMX fragment) ---
    r = client.post(
        f"/ui/plans/{pid}/board/bulk_issues",
        data={"kind": "tasks", "only_open": "on"},
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200, r.text
    assert 'id="flash"' in r.text
    assert "Created 1 issues" in r.text

    # --- Create/Update branch (HTMX fragment) ---
    r2 = client.post(
        f"/ui/plans/{pid}/git/branch",
        data={"branch": f"feature/{pid}"},
        headers={"HX-Request": "true"},
    )
    assert r2.status_code == 200, r2.text
    assert 'id="flash"' in r2.text
    assert "Branch updated" in r2.text

    # --- Open PR (HTMX fragment) ---
    r3 = client.post(
        f"/ui/plans/{pid}/git/pr",
        data={"branch": f"feature/{pid}", "title": "My PR"},
        headers={"HX-Request": "true"},
    )
    assert r3.status_code == 200, r3.text
    assert 'id="flash"' in r3.text
    assert "PR opened" in r3.text

    # --- Clean up overrides ---
    app.dependency_overrides.pop(ui_plans.get_current_user, None)
