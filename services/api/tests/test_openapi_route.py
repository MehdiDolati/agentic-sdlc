from starlette.testclient import TestClient
from services.api.app import app, _retarget_store


def test_openapi_route_ok(tmp_path):
    _retarget_store(tmp_path)
    c = TestClient(app)
    r = c.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "openapi" in data
    assert "paths" in data
