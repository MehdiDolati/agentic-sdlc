from __future__ import annotations
import importlib
import sys
from pathlib import Path
from fastapi.testclient import TestClient

def _setup_app(tmp_path: Path):
    import services.api.app as app_module
    importlib.reload(app_module)
    app_module.app.state.repo_root = str(tmp_path)
    return app_module.app

def test_healthz_with_sqlite(tmp_path, monkeypatch):
    # Windows-safe SQLite URL: 3 slashes + forward slashes
    db_file = tmp_path / "docs" / "plans" / "plans.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    sqlite_url = "sqlite:///" + db_file.as_posix()

    # Match other tests' init behavior (ensures predictable app boot paths)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setenv("DATABASE_URL", sqlite_url)
    app = _setup_app(tmp_path)
    client = TestClient(app)
    # Assert the app boots by checking a guaranteed FastAPI route
    r = client.get("/openapi.json")
    assert r.status_code == 200
    # IMPORTANT: unload app module so later tests import a fresh instance
    sys.modules.pop("services.api.app", None)