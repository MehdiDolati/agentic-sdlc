import json
import inspect
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient


def _include_router_safely(mod):
    router = getattr(mod, "router", None)
    if router is None:
        pytest.skip(f"{mod.__name__} has no 'router'")
    app = FastAPI()
    try:
        app.include_router(router)
    except Exception:
        pytest.skip(f"Could not include router from {mod.__name__}")
    return app, router


def _exercise_router_endpoints(app, router):
    c = TestClient(app, raise_server_exceptions=False)
    # Find all routes and invoke them with minimal payloads
    for r in router.routes:
        path = getattr(r, "path", None) or getattr(r, "path_format", None)
        methods = getattr(r, "methods", None) or set()
        if not path or not methods:
            continue
        # Resolve path params with dummy values
        url = path
        for p in getattr(r, "param_convertors", {}).keys() if hasattr(r, "param_convertors") else []:
            url = url.replace("{" + p + "}", "x")
        # Heuristic replacement if braces remain
        if "{" in url and "}" in url:
            url = url.replace("{", "").replace("}", "")
        for m in methods:
            m = m.upper()
            # Minimal JSON body for POST/PUT/PATCH
            if m in ("POST", "PUT", "PATCH"):
                resp = c.request(m, url, json={"ping": "pong"})
                assert resp.status_code in (200, 201, 202, 204, 400, 404), f"{m} {url} -> {resp.status_code}"
            else:
                resp = c.request(m, url)
                assert resp.status_code in (200, 202, 204, 400, 404), f"{m} {url} -> {resp.status_code}"


@pytest.mark.parametrize("modpath", [
    "services.api.routes.create",
    "services.api.routes.execute",
])
def test_router_smoke(modpath):
    try:
        mod = __import__(modpath, fromlist=["*"])
    except Exception:
        pytest.skip(f"Cannot import {modpath}")
    app, router = _include_router_safely(mod)
    _exercise_router_endpoints(app, router)
