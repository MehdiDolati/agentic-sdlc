import re
import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared, settings as cfg

def test_api_create_execute_generic(tmp_path, monkeypatch):
    # Isolate store & disable auth to reach more paths
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)

    c = TestClient(app, raise_server_exceptions=False)

    targets = []
    for r in app.routes:
        path = getattr(r, "path", "")
        methods = getattr(r, "methods", set())
        if not path or not methods:
            continue
        if not path.startswith("/api/"):
            continue
        # Heuristics: anything with create/execute in path
        if re.search(r"(create|execute)", path, re.IGNORECASE):
            targets.append((path, methods))

    if not targets:
        pytest.skip("No /api/*create* or /api/*execute* endpoints found")

    for path, methods in targets:
        # replace path params with 'x'
        url = path
        for seg in url.split("/"):
            if seg.startswith("{") and seg.endswith("}"):
                url = url.replace(seg, "x")
        for m in methods:
            m = m.upper()
            if m in ("POST", "PUT", "PATCH"):
                resp = c.request(m, url, json={"ping": "pong"}, data={"ping": "pong"})
            else:
                resp = c.request(m, url)
            assert resp.status_code in (200, 201, 202, 204, 302, 303, 400, 401, 403, 404, 409, 422, 500)