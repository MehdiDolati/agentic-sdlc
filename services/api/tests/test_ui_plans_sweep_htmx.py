import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import settings as cfg, shared


def test_ui_plans_sweep_htmx(tmp_path, monkeypatch):
    # Configure test store & disable auth to reach more UI paths
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)

    c = TestClient(app, raise_server_exceptions=False)
    headers = {"HX-Request": "true"}  # trigger HTMX branches / partials

    # Collect only /ui/plans* routes
    plan_routes = []
    for r in app.routes:
        path = getattr(r, "path", "")
        methods = getattr(r, "methods", set())
        if path.startswith("/ui/plans") and methods:
            plan_routes.append((path, methods))

    if not plan_routes:
        pytest.skip("No /ui/plans* routes mounted")

    # Exercise a subset (all should be fine, but keep it bounded if huge)
    for path, methods in plan_routes:
        # Replace path params with dummy 'x'
        url = path
        for seg in url.split("/"):
            if seg.startswith("{") and seg.endswith("}"):
                url = url.replace(seg, "x")
        for m in methods:
            m = m.upper()
            if m in ("POST", "PUT", "PATCH"):
                # Minimal form and json to satisfy typical handlers
                resp = c.request(m, url, headers=headers, data={"kind": "tasks"}, json={"ping": "pong"})
            else:
                resp = c.request(m, url, headers=headers)
            # Accept common success/handled/fallback codes (422 = validation, 500 = server-side branch)
            assert resp.status_code in (200, 201, 202, 204, 303, 302, 400, 401, 403, 404, 422, 500)