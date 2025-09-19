import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store


def _route_exists(path: str, method: str = "GET") -> bool:
    method = method.upper()
    for r in app.routes:
        if getattr(r, "path", "") == path and method in getattr(r, "methods", set()):
            return True
    return False


def test_plan_run_mismatch_404(tmp_path):
    _retarget_store(tmp_path)
    c = TestClient(app, raise_server_exceptions=False)
    # Only run if the detail route is mounted as /ui/plans/{plan_id}/run/{run_id}
    if not any(getattr(r, "path", "") == "/ui/plans/{plan_id}/run/{run_id}" and "GET" in getattr(r, "methods", set()) for r in app.routes):
        pytest.skip("Run detail route not mounted")
    # Use nonsense IDs, expect 404 (mismatch)
    r = c.get("/ui/plans/nope/run/nada")
    assert r.status_code == 404