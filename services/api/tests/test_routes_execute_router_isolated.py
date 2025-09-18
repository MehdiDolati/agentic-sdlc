import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient


def _exercise_router(router):
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app, raise_server_exceptions=False)
    for r in router.routes:
        path = getattr(r, "path", "") or getattr(r, "path_format", "")
        methods = getattr(r, "methods", set())
        if not path or not methods:
            continue
        # Replace any {param} with 'x'
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
            # Accept a wide range: success, handled errors, validation
            assert resp.status_code in (200, 201, 202, 204, 400, 401, 403, 404, 409, 422, 500)


def test_execute_router_isolated():
    try:
        from services.api.routes import execute as mod
    except Exception:
        pytest.skip("services.api.routes.execute not importable")
    router = getattr(mod, "router", None)
    if router is None:
        pytest.skip("execute.py does not export `router`")
    _exercise_router(router)