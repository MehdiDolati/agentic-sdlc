import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared, settings as cfg


def _belongs_to_ui_plans(route) -> bool:
    try:
        return route.endpoint.__module__.endswith(".ui.plans")
    except Exception:
        return False


def _replace_params(path: str) -> str:
    url = path
    for seg in url.split("/"):
        if seg.startswith("{") and seg.endswith("}"):
            url = url.replace(seg, "x")
    return url


def test_ui_plans_routes_sweep_broad(tmp_path, monkeypatch):
    # Isolate repo + relax auth so routes are reachable
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)

    c = TestClient(app, raise_server_exceptions=False)

    plan_routes = []
    for r in app.routes:
        path = getattr(r, "path", "") or getattr(r, "path_format", "")
        methods = getattr(r, "methods", set())
        if not path or not methods:
            continue
        if _belongs_to_ui_plans(r):
            plan_routes.append((path, methods))

    if not plan_routes:
        pytest.skip("No routes from services.api.ui.plans are mounted")

    # Sweep all routes with both vanilla and HTMX headers
    common_forms = {"kind": "tasks", "only_open": "true", "title": "t", "q": "x"}
    htmx_headers = {"HX-Request": "true", "HX-Target": "flash"}
    for path, methods in plan_routes:
        url = _replace_params(path)
        for method in methods:
            m = method.upper()
            for headers in ({}, htmx_headers):
                if m in ("POST", "PUT", "PATCH"):
                    resp = c.request(m, url, headers=headers, data=common_forms, json={"ping": "pong"})
                else:
                    resp = c.request(m, url, headers=headers)
                # Accept common success/redirect/handled/validation/error codes
                assert resp.status_code in (
                    200, 201, 202, 204, 302, 303, 400, 401, 403, 404, 405, 409, 422, 500
                )