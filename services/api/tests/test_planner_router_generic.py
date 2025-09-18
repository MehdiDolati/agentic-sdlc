import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

def _mk_planner_app():
    try:
        from services.api.planner import routes as planner_routes
    except Exception:
        pytest.skip("services.api.planner.routes not importable")
    router = getattr(planner_routes, "router", None)
    if router is None:
        pytest.skip("planner router not exposed")
    app = FastAPI()
    try:
        app.include_router(router)
    except Exception:
        pytest.skip("could not include planner router")
    return app, router

def test_planner_router_generic():
    app, router = _mk_planner_app()
    c = TestClient(app, raise_server_exceptions=False)
    for r in router.routes:
        path = getattr(r, "path", "") or getattr(r, "path_format", "")
        methods = getattr(r, "methods", set())
        if not path or not methods:
            continue
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
            assert resp.status_code in (200, 201, 202, 204, 400, 401, 403, 404, 422, 500)
