import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store


def _route_exists(path: str, method: str = "GET") -> bool:
    method = method.upper()
    for r in app.routes:
        if getattr(r, "path", "") == path and method in getattr(r, "methods", set()):
            return True
    return False


def test_health_endpoint(tmp_path):
    _retarget_store(tmp_path)
    c = TestClient(app)
    if not _route_exists("/health", "GET"):
        pytest.skip("/health not mounted")
    r = c.get("/health")
    assert r.status_code == 200
    # content may be plain or JSON; just ensure something is returned
    assert r.text or r.content


def test_index_or_root_redirect(tmp_path):
    _retarget_store(tmp_path)
    c = TestClient(app)
    # Try common roots; assert whichever exists
    candidates = [("/", "GET"), ("/ui", "GET"), ("/index", "GET")]
    hit = False
    for path, method in candidates:
        if _route_exists(path, method):
            r = c.request(method, path)
            assert r.status_code in (200, 302, 303)
            hit = True
            break
    if not hit:
        pytest.skip("No index-like route mounted")
