import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from services.api.app import app as main_app


def _route_exists(app, path: str, method: str = "GET") -> bool:
    method = method.upper()
    for r in app.routes:
        if getattr(r, "path", "") == path and method in getattr(r, "methods", set()):
            return True
    return False


def test_http_404_handler_normal():
    c = TestClient(main_app, raise_server_exceptions=False)
    r = c.get("/__definitely_missing__")
    assert r.status_code == 404
    assert r.text  # render body (template or json)


def test_http_404_handler_htmx():
    c = TestClient(main_app, raise_server_exceptions=False)
    r = c.get("/__definitely_missing__", headers={"HX-Request": "true"})
    assert r.status_code == 404
    # body should still be non-empty (htmx partial or message)
    assert r.text


def test_http_500_handler_htmx_injected_route():
    """
    Inject a crashing route into a tiny sub-app and mount it under the main app,
    so the main error handlers process the exception. If the mount fails, skip.
    """
    sub = FastAPI()
    @sub.get("/boom")
    def boom():
        raise RuntimeError("boom")

    # Try to mount under a unique prefix to avoid collisions
    prefix = "/__crash__"
    try:
        main_app.mount(prefix, sub)
    except Exception:
        pytest.skip("Could not mount crash app; skipping 500 handler test")

    c = TestClient(main_app, raise_server_exceptions=False)
    r = c.get(prefix + "/boom", headers={"HX-Request": "true"})
    assert r.status_code == 500
    assert r.text
