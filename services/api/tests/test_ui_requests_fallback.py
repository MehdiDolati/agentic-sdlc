import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.routes import ui_requests


def test_submit_request_openapi_fallback(monkeypatch, tmp_path):
    """
    If generate_openapi raises, the submit_request view should fall back to a
    conservative OpenAPI skeleton (empty paths).
    """
    _retarget_store(tmp_path)

    # Force generate_openapi to throw an exception
    def fail_generate(_blueprint):
        raise RuntimeError("openapi failure")

    monkeypatch.setattr(ui_requests, "generate_openapi", fail_generate)

    client = TestClient(app)
    resp = client.post(
        "/ui/requests",
        data={"project_vision": "Test vision", "agent_mode": "single", "llm_provider": "none"},
    )
    assert resp.status_code == 200
    # The fallback skeleton has an empty paths object – ensure it is present in the rendered output
    assert '"paths": {}' in resp.text or '"paths":{}' in resp.text