from pathlib import Path
from fastapi.testclient import TestClient

from services.api.app import app
import services.api.core.shared as shared
from services.api.core.settings import load_settings

client = TestClient(app)

def test_settings_get_and_save(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))

    # GET page
    r = client.get("/ui/settings")
    assert r.status_code == 200
    assert "Settings" in r.text
    assert "Planner" in r.text

    # POST save
    r2 = client.post(
        "/ui/settings",
        data={
            "planner_mode": "multi",
            "default_provider": "openai",
            "api_base_url": "https://api.local",
            "auth_enabled": "on",
            "multi_agent_enabled": "on",
        },
    )
    assert r2.status_code == 200
    assert "Saved." in r2.text

    # Verify persisted file
    cfg = load_settings(shared._repo_root())
    assert cfg["planner_mode"] == "multi"
    assert cfg["default_provider"] == "openai"
    assert cfg["api_base_url"] == "https://api.local"
    assert cfg["auth_enabled"] is True
    assert cfg["multi_agent_enabled"] is True
