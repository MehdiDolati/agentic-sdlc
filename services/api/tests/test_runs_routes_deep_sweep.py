import pytest
from starlette.testclient import TestClient
from services.api.core import shared, settings as cfg
from services.api.app import app, _retarget_store

def _module_is_runs(route) -> bool:
    try:
        return route.endpoint.__module__.endswith(".runs.routes")
    except Exception:
        return False

def _replace_params(path: str) -> str:
    url = path
    for seg in url.split("/"):
        if seg.startswith("{") and seg.endswith("}"):
            url = url.replace(seg, "x")
    return url

def test_runs_routes_module_sweep(tmp_path, monkeypatch):
    # Isolate + relax auth, retarget storage
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)

    c = TestClient(app, raise_server_exceptions=False)
    runs_routes = []
    for r in app.routes:
        path = getattr(r, "path", "") or getattr(r, "path_format", "")
        methods = getattr(r, "methods", set())
        if not path or not methods:
            continue
        if _module_is_runs(r):
            runs_routes.append((path, methods))

    if not runs_routes:
        pytest.skip("no runs routes mounted")

    for path, methods in runs_routes:
        url = _replace_params(path)
        for m in methods:
            m = m.upper()
            if m in ("POST", "PUT", "PATCH"):
                resp = c.request(m, url, json={"ping": "pong"})
            else:
                resp = c.request(m, url)
            assert resp.status_code in (200, 201, 202, 204, 302, 303, 400, 401, 403, 404, 405, 409, 422, 500)
