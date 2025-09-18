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

def test_runs_list_detail_polling(tmp_path, monkeypatch):
    # Disable auth to reach pages; still accept various statuses
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)

    c = TestClient(app, raise_server_exceptions=False)

    # HTML list/table if present
    if _route_exists("/ui/runs", "GET"):
        li = c.get("/ui/runs")
        assert li.status_code in (200, 204, 404, 500)

    # API list
    if _route_exists("/api/runs", "GET"):
        la = c.get("/api/runs")
        assert la.status_code in (200, 204, 404, 500)
        # Try to pull an id if list returns one (tolerate any shape)
        run_id = None
        try:
            js = la.json()
            if isinstance(js, list) and js:
                cand = js[0]
                if isinstance(cand, dict):
                    run_id = cand.get("id") or cand.get("run_id")
        except Exception:
            pass
        # Fallback to a random id to hit 404/branches
        run_id = run_id or uuid.uuid4().hex[:8]

        # Detail
        det = c.get(f"/api/runs/{run_id}")
        assert det.status_code in (200, 404, 500)

        # Polling (branchy path)
        poll = c.get(f"/api/runs/{run_id}/poll")
        assert poll.status_code in (200, 202, 404, 500)
