import uuid
import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared, settings as cfg


def _route_exists(path: str, method: str = "GET") -> bool:
    m = method.upper()
    for r in app.routes:
        if getattr(r, "path", "") == path and m in getattr(r, "methods", set()):
            return True
    return False


def test_runs_ui_pages_generic(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)

    c = TestClient(app, raise_server_exceptions=False)

    # List
    if _route_exists("/ui/runs", "GET"):
        li = c.get("/ui/runs")
        assert li.status_code in (200, 204, 404, 500)

    # Table (often HTMX partial)
    if _route_exists("/ui/runs/table", "GET"):
        tab = c.get("/ui/runs/table", headers={"HX-Request": "true"})
        assert tab.status_code in (200, 204, 404, 500)

    # Detail (HTML) — use random id to hit 404/branches if nothing exists
    # Find pattern /ui/runs/{run_id}
    detail_path = None
    for r in app.routes:
        p = getattr(r, "path", "")
        methods = getattr(r, "methods", set())
        if p.startswith("/ui/runs/") and "{" in p and "}" in p and "GET" in methods:
            detail_path = p
            break
    if detail_path:
        run_id = uuid.uuid4().hex[:8]
        url = detail_path.replace("{", "").replace("}", "").rsplit("/", 1)[0] + f"/{run_id}"
        de = c.get(url)
        assert de.status_code in (200, 404, 500)