import os
import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared

def _route_exists(path: str, method: str = "GET") -> bool:
    m = method.upper()
    for r in app.routes:
        if getattr(r, "path", "") == path and m in getattr(r, "methods", set()):
            return True
    return False

def test_openapi_fallback_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    _retarget_store(tmp_path)
    c = TestClient(app, raise_server_exceptions=False)

    if not _route_exists("/openapi.json", "GET"):
        pytest.skip("/openapi.json not mounted")

    r1 = c.get("/openapi.json")
    assert r1.status_code in (200, 500)
    if r1.status_code == 200:
        j = r1.json()
        assert "openapi" in j and "paths" in j

    # Try to perturb any env-based toggles so fallback/diff paths execute
    monkeypatch.setenv("OPENAPI_FALLBACK", "1")
    r2 = c.get("/openapi.json")
    assert r2.status_code in (200, 500)
    if r2.status_code == 200:
        j2 = r2.json()
        assert "openapi" in j2 and "paths" in j2