import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store


def _route_exists(path: str, method: str = "GET") -> bool:
    method = method.upper()
    for r in app.routes:
        if getattr(r, "path", "") == path and method in getattr(r, "methods", set()):
            return True
    return False


def test_openapi_json(tmp_path):
    _retarget_store(tmp_path)
    c = TestClient(app, raise_server_exceptions=False)
    if not _route_exists("/openapi.json", "GET"):
        pytest.skip("/openapi.json not mounted")
    r = c.get("/openapi.json")
    assert r.status_code == 200
    j = r.json()
    assert "openapi" in j and "paths" in j


def test_docs_if_enabled(tmp_path):
    _retarget_store(tmp_path)
    c = TestClient(app, raise_server_exceptions=False)
    # FastAPI often mounts /docs; accept skip if disabled
    if not _route_exists("/docs", "GET"):
        pytest.skip("/docs not mounted")
    r = c.get("/docs")
    assert r.status_code in (200, 307, 308)  # serve or redirect to swagger UI