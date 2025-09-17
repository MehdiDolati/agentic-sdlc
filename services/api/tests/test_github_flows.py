import os
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared
from services.api.core.repos import PlansRepoDB, ensure_plans_schema
from services.api.core.repos import RunsRepoDB, ensure_runs_schema


def _setup_plan_with_tasks(tmp_path):
    """
    Create a plan with a tasks file containing two tasks (one open, one closed).
    Returns the plan_id.
    """
    os.environ["REPO_ROOT"] = str(tmp_path)
    shared._reset_repo_root_cache_for_tests()
    engine = shared._create_engine(shared._database_url(str(tmp_path)))
    ensure_plans_schema(engine)
    plan_id = "pln"
    PlansRepoDB(engine).create({"id": plan_id, "request": "goal", "owner": "public", "artifacts": {}, "status": "new"})
    # Write tasks markdown
    tasks_rel = f"docs/tasks/{plan_id}.md"
    tasks_file = tmp_path / tasks_rel
    tasks_file.parent.mkdir(parents=True, exist_ok=True)
    tasks_file.write_text("- [ ] First task\n- [x] Done task\n", encoding="utf-8")
    # Persist artifact path in DB
    PlansRepoDB(engine).update_artifacts(plan_id, {"tasks": tasks_rel})
    return plan_id, tasks_rel


def test_bulk_issues_not_configured(monkeypatch, tmp_path):
    """
    When GitHub is not configured, bulk_issues should render an error flash.
    """
    plan_id, _ = _setup_plan_with_tasks(tmp_path)
    _retarget_store(tmp_path)
    # Remove any GitHub configuration
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    monkeypatch.delenv("GITHUB_DEFAULT_BRANCH", raising=False)
    # Ensure we are NOT in the stubbed test-mode path
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/ui/plans/{plan_id}/board/bulk_issues", data={"kind": "tasks", "only_open": "true"})
    assert resp.status_code == 200
    assert "GitHub not configured." in resp.text


def test_bulk_issues_unauthorized(monkeypatch, tmp_path):
    """
    Simulate a GitHub API 401/403 to ensure the error message is surfaced.
    """
    plan_id, _ = _setup_plan_with_tasks(tmp_path)
    _retarget_store(tmp_path)
    # Provide fake token/repo
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPO", "owner/repo")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)  # force real GH code path

    # Patch GH.create_issue to raise a real requests.HTTPError with status_code 401
    from services.api.integrations import github as gh_module
    import requests

    def fake_create_issue(self, *args, **kwargs):
        r = requests.Response()
        r.status_code = 401
        # Optionally set url to make the repr nicer (not required)
        r.url = "https://api.github.com/repos/owner/repo/issues"
        raise requests.HTTPError(response=r)

    monkeypatch.setattr(gh_module.GH, "create_issue", fake_create_issue, raising=False)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/ui/plans/{plan_id}/board/bulk_issues", data={"kind": "tasks", "only_open": "true"})
    assert resp.status_code == 401
    assert "GitHub unauthorized." in resp.text


def test_bulk_issues_success(monkeypatch, tmp_path):
    """
    In test mode (PYTEST_CURRENT_TEST), issues are created locally and IDs assigned.
    """
    plan_id, tasks_rel = _setup_plan_with_tasks(tmp_path)
    _retarget_store(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPO", "owner/repo")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "true")
    # Ensure success even if the route still goes through GH path
    from services.api.integrations import github as gh_module
    monkeypatch.setattr(
        gh_module.GH,
        "create_issue",
        lambda self, title, body="", labels=None: {"number": 1, "html_url": "https://github.com/owner/repo/issues/1"},
        raising=False,
    )

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/ui/plans/{plan_id}/board/bulk_issues", data={"kind": "tasks", "only_open": "true"})
    assert resp.status_code == 200
    # Should mention the number of issues created in the flash
    assert "Created 1 issues" in resp.text or "Created 2 issues" in resp.text
    # The tasks file should now contain an ID for the open task
    tasks_path = tmp_path / tasks_rel
    updated = tasks_path.read_text(encoding="utf-8")
    assert "(#1)" in updated or "(#2)" in updated