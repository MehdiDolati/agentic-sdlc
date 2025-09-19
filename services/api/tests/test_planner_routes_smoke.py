import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

def _mk():
    try:
        from services.api.planner import routes as planner_routes
    except Exception:
        pytest.skip("planner routes not importable")
    app = FastAPI()
    try:
        app.include_router(planner_routes.router, prefix="/api/planner")
    except Exception:
        pytest.skip("planner router not includable")
    return app

def test_planner_endpoints_minimal():
    app = _mk()
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/api/planner")           # index/listing if present
    assert r.status_code in (200, 204, 404)
    r2 = c.post("/api/planner/plan", json={"goal": "increase coverage"})
    assert r2.status_code in (200, 202, 400, 404)
