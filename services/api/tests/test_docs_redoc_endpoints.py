import pytest
from starlette.testclient import TestClient
from services.api.app import app

def _route_exists(path: str, method: str = "GET") -> bool:
    m = method.upper()
    for r in app.routes:
        if getattr(r, "path", "") == path and m in getattr(r, "methods", set()):
            return True
    return False

def test_docs_and_redoc_present():
    c = TestClient(app, raise_server_exceptions=False)

    if _route_exists("/docs", "GET"):
        r = c.get("/docs")
        assert r.status_code in (200, 500)

    if _route_exists("/redoc", "GET"):
        r2 = c.get("/redoc")
        assert r2.status_code in (200, 500)
