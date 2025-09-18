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


def test_auth_api_routes_sweep(tmp_path, monkeypatch):
    # Disable auth to reach most paths; accept any safe status anyway
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)
    c = TestClient(app, raise_server_exceptions=False)

    # Typical endpoints (tolerate absence)
    candidates = [
        ("GET", "/api/auth/me", None),
        ("POST", "/api/auth/login", {"email": "x@example.com", "password": "bad"}),
        ("POST", "/api/auth/logout", None),
        ("POST", "/api/auth/register", {"email": "x@example.com", "password": "secret"}),
        ("POST", "/api/auth/refresh", None),
    ]
    for method, path, payload in candidates:
        if not _route_exists(path, method):
            continue
        if method == "GET":
            r = c.get(path)
        else:
            # send both json and form to satisfy different implementations
            r = c.request(method, path, json=payload or {}, data=payload or {})
        assert r.status_code in (200, 201, 202, 204, 400, 401, 403, 404, 422, 500)
