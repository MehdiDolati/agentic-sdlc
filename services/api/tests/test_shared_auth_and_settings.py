from pathlib import Path
from services.api.core.shared import _repo_root, _auth_enabled
from services.api.core.settings import update_settings, load_settings

def test_repo_root_prefers_app_state_dir(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    assert _repo_root() == tmp_path

def test_auth_env_overrides_settings(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    # Persist auth_enabled = False
    update_settings(tmp_path, {"auth_enabled": False})
    assert load_settings(tmp_path)["auth_enabled"] is False
    # But ENV must win
    monkeypatch.setenv("AUTH_MODE", "on")
    assert _auth_enabled() is True
    monkeypatch.setenv("AUTH_MODE", "off")
    assert _auth_enabled() is False
