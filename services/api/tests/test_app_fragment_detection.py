from starlette.testclient import TestClient
from services.api.app import app, _retarget_store


def test_wants_fragment_via_htmx(tmp_path):
    _retarget_store(tmp_path)
    c = TestClient(app, raise_server_exceptions=False)
    # hits a 404 so we go through the exception handler, which chooses fragment for HTMX
    r = c.get("/api/notes/does-not-exist", headers={"HX-Request": "true"})
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("text/html")


def test_wants_json_without_htmx(tmp_path):
    _retarget_store(tmp_path)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/api/notes/does-not-exist")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
