import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store


def test_http_404_handler_htmx(tmp_path):
    """
    When an HTTPException (e.g. 404) is raised and the request is from HTMX,
    the custom handler should return an HTML flash fragment rather than JSON.
    """
    _retarget_store(tmp_path)
    client = TestClient(app, raise_server_exceptions=False)
    # Trigger a 404 via the notes API
    resp = client.get("/api/notes/nonexistent", headers={"HX-Request": "true"})
    assert resp.status_code == 404
    # The content-type should be HTML and the response should include flash content
    assert resp.headers["content-type"].startswith("text/html")
    # Should not leak generic unexpected error message
    assert "Unexpected error." not in resp.text
    # The flash template will display either the status code or the detail text (e.g. "Note not found")
    assert "404" in resp.text or "Note not found" in resp.text


def test_http_404_handler_json(tmp_path):
    """
    Without HTMX, 404 errors should be returned as JSON with the detail.
    """
    _retarget_store(tmp_path)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/notes/nonexistent")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["detail"] == "Note not found"


def test_unhandled_exception_handlers(tmp_path):
    """
    Generic exceptions should be handled without leaking internals.
    HTMX requests get an HTML fragment; other requests get JSON.
    """
    _retarget_store(tmp_path)

    # Dynamically register an endpoint that raises a runtime error
    async def boom():
        raise RuntimeError("boom")

    app.add_api_route("/boom", boom)
    client = TestClient(app, raise_server_exceptions=False)

    # HTMX request yields a 500 HTML response with generic error message
    resp = client.get("/boom", headers={"HX-Request": "true"})
    assert resp.status_code == 500
    assert resp.headers["content-type"].startswith("text/html")
    assert "Unexpected error." in resp.text

    # Non-HTMX request yields JSON with the generic message
    resp2 = client.get("/boom")
    assert resp2.status_code == 500
    assert resp2.headers["content-type"].startswith("application/json")
    assert resp2.json()["detail"] == "Unexpected error."

