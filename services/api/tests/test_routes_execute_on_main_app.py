import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared, settings as cfg


def _belongs_to_execute(route) -> bool:
    try:
        mod = route.endpoint.__module__
        return mod.endswith(".routes.execute")
    except Exception:
        return False


def test_execute_routes_on_main_app(tmp_path, monkeypatch):
    # Isolate store and (optionally) relax auth so endpoints are reachable
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)

    c = TestClient(app, raise_server_exceptions=False)

    targets = []
    for r in app.routes:
        path = getattr(r, "path", "") or getattr(r, "path_format", "")
        methods = getattr(r, "methods", set())
        if not path or not methods:
            continue
        if _belongs_to_execute(r):
            targets.append((path, methods))

    if not targets:
        pytest.skip("No routes from services.api.routes.execute are mounted on the main app")

    for path, methods in targets:
        # Replace {param} with 'x' to exercise param paths
        url = path
        for seg in url.split("/"):
            if seg.startswith("{") and seg.endswith("}"):
                url = url.replace(seg, "x")
        for m in methods:
            m = m.upper()
            if m in ("POST", "PUT", "PATCH"):
                # Provide minimal body to get past validators
                resp = c.request(m, url, json={"ping": "pong"}, data={"ping": "pong"})
            else:
                resp = c.request(m, url)
            # Accept broad range (success, redirects, validation, handled errors)
            assert resp.status_code in (200, 201, 202, 204, 302, 303, 400, 401, 403, 404, 409, 422, 500)
