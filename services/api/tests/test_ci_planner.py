from __future__ import annotations
from pathlib import Path
import json
import os
import importlib
import types

def _reload_app(tmp_path: Path) -> types.ModuleType:
    # Force app.py to use this tmp repo root (as in other tests)
    import services.api.app as appmod
    importlib.reload(appmod)
    appmod.app.state.repo_root = str(tmp_path)
    return appmod

def test_ci_planner_generates_artifacts_and_db_row(tmp_path, monkeypatch):
    # Arrange: fake PR event
    event = {
        "pull_request": {
            "number": 123,
            "title": "Add planner CI check",
            "user": {"login": "octocat"},
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.chdir(tmp_path)

    # Reset app module (so helper paths use tmp_path)
    appmod = _reload_app(tmp_path)

    # Import the CI runner
    import sys
    sys.path.insert(0, str((tmp_path / "scripts").resolve()))
    # Create an in-tree copy reference so import works (in repo it's at scripts/)
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(exist_ok=True, parents=True)
    # In real repo, scripts/ci_planner.py already exists. For tests, we import from the repo tree:
    sys.path.insert(0, str(Path.cwd()))  # ensure repo root on path
    import scripts.ci_planner as ci_planner  # type: ignore

    # Act
    rc = ci_planner.main()
    assert rc == 0

    # Assert: artifacts exist (deterministic names)
    # We don't guess exact slug; just verify expected directories have a file
    docs = tmp_path / "docs"
    assert any((docs / "prd").rglob("PRD-*.md"))
    assert any((docs / "api" / "generated").rglob("openapi-*.yaml"))
    assert any((docs / "adrs").rglob("ADR-*.md"))
    assert any((docs / "stories").rglob("STORIES-*.md"))
    assert any((docs / "tasks").rglob("TASKS-*.md"))

    # Assert: a plan was persisted in DB
    engine = appmod._create_engine(appmod._database_url(tmp_path))
    # Find the newest plan_id via index.json (compat layer)
    index_path = docs / "plans" / "index.json"
    assert index_path.exists()
    idx = json.loads(index_path.read_text(encoding="utf-8"))
    assert isinstance(idx, dict) and idx, "index.json should have at least one plan"
    # Get any plan_id; verify DB row exists and matches request owner
    plan_id, entry = next(iter(idx.items()))
    row = appmod.PlansRepoDB(engine).get(plan_id)
    assert row and row["id"] == plan_id
    assert "PR #123: Add planner CI check" in row["request"]
    assert row["owner"] == "octocat"
    # Artifacts mapping persisted
    arts = row.get("artifacts") or {}
    for key in ("prd", "openapi", "adr", "stories", "tasks"):
        assert key in arts and isinstance(arts[key], str)
        assert (tmp_path / arts[key]).exists()

def test_ci_planner_writes_summary_and_outputs(tmp_path, monkeypatch):
    # Arrange: stub PR data via env variables (works when no event file)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    monkeypatch.setenv("PR_NUMBER", "456")
    monkeypatch.setenv("PR_TITLE", "Planner outputs smoke")

    # Prepare summary and outputs files (GitHub Actions conventions)
    summary_file = tmp_path / "summary.md"
    output_file = tmp_path / "outputs.txt"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    # Repo root for this test
    monkeypatch.chdir(tmp_path)
    appmod = _reload_app(tmp_path)

    import sys
    sys.path.insert(0, str(Path.cwd()))
    import scripts.ci_planner as ci_planner  # type: ignore

    # Act
    rc = ci_planner.main()
    assert rc == 0

    # Assert: summary contains headline and plan_id line
    assert summary_file.exists()
    text = summary_file.read_text(encoding="utf-8")
    assert "### Planner Execution" in text
    assert "plan_id" in text

    # Assert: outputs file has plan_id and artifact paths
    assert output_file.exists()
    out_text = output_file.read_text(encoding="utf-8")
    assert "plan_id=" in out_text
    assert "prd_path=" in out_text
    assert "openapi_path=" in out_text
