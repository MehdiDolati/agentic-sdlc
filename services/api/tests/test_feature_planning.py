import json
from pathlib import Path

from fastapi.testclient import TestClient

from services.api.app import app, _retarget_store, _create_engine, _database_url


def test_feature_planning_with_db_plan(tmp_path, monkeypatch):
    """Save a plan via the save-all route (DB) then run feature-planning.

    This test verifies the DB-backed path for the new feature-planning
    endpoint. It runs entirely against a temporary store (no repo files).
    """
    # Ensure proper environment isolation
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    
    # Reset repo root cache to ensure changes take effect
    from services.api.core import shared
    shared._reset_repo_root_cache_for_tests()
    
    # Retarget store to temp dir so files are written under tmp_path
    _retarget_store(tmp_path)

    # Initialize database schema - ensure all required tables exist
    # We need to ensure the database directory exists first
    (tmp_path / "docs" / "plans").mkdir(parents=True, exist_ok=True)
    
    from services.api.core.repos import ensure_plans_schema, ensure_projects_schema, ensure_features_schema, ensure_priority_changes_schema
    
    # Verify that both database URLs point to the same location
    test_db_url = _database_url(tmp_path)
    api_db_url = _database_url(shared._repo_root())
    assert test_db_url == api_db_url, f"Database URLs don't match: test={test_db_url}, api={api_db_url}"
    
    engine = _create_engine(test_db_url)
    ensure_projects_schema(engine)
    ensure_plans_schema(engine)
    ensure_features_schema(engine)
    ensure_priority_changes_schema(engine)

    client = TestClient(app)

    project_id = "proj-20250101010101-plan-aaaaaa"
    plan_id = "20250101010101-plan-aaaaaa"

    # Save a simple plan via the save-all endpoint (creates DB row + plan file)
    payload = {
        "project_id": project_id,
        "project_name": "Test Project",
        "plans": [
            {
                "id": plan_id,
                "name": "Build test service",
                "description": "A test plan",
                "priority": "high",
                "priority_order": 1,
                "size_estimate": 3,
                "features": []
            }
        ]
    }

    r = client.post("/plans/save-all", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("success") is True

    # Now call feature-planning
    r2 = client.post(f"/plans/project/{project_id}/feature-planning")
    assert r2.status_code == 200, r2.text
    res = r2.json()
    assert res.get("success") is True
    assert res.get("user_stories_count", 0) >= 1

    # stories_file should be written under tmp_path/docs/stories
    stories_path = Path(res.get("stories_file"))
    assert stories_path.exists()
    # Ensure the file contains the expected project_id and plan_id
    content = json.loads(stories_path.read_text(encoding="utf-8"))
    assert content.get("project_id") == project_id
    assert content.get("plan_id") == plan_id
