from pathlib import Path
from fastapi.testclient import TestClient
from services.api.app import app

client = TestClient(app)

def test_openapi_fallback_in_requests_form(monkeypatch, tmp_path: Path):
    # Force planner root & make generate_openapi raise
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    import services.api.routes.ui_requests as ui_req
    orig = ui_req.generate_openapi
    def explode(*_a, **_k): raise RuntimeError("no generator")
    try:
        ui_req.generate_openapi = explode
        r = client.post("/ui/requests", data={"project_vision":"X","agent_mode":"single","llm_provider":"none"})
        #r = client.post("/ui/requests", data={"text": "mamad"})
        assert r.status_code == 200
        # Fallback renders review template (contains OpenAPI section)
        assert "OpenAPI" in r.text
    finally:
        ui_req.generate_openapi = orig
