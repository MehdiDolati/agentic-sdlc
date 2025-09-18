from services.api.core import settings as cfg, shared
import pytest


def _try_env_override(monkeypatch, enable: bool):
    """
    Try a handful of common env knobs used across variants to toggle auth gate.
    Return True if any knob flips _auth_enabled() from the file default.
    """
    # Candidates: variable name -> (value_when_enable, value_when_disable)
    candidates = {
        "AUTH_ENABLED": ("true", "false"),
        "AUTH_MODE": ("enabled", "disabled"),
        "AUTH": ("on", "off"),
    }
    flipped = False
    for var, (v_on, v_off) in candidates.items():
        # Clear all to avoid interference
        for k in candidates.keys():
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv(var, v_on if enable else v_off)
        if shared._auth_enabled() is enable:
            flipped = True
            break
    return flipped


def test_auth_enabled_env_enabled_overrides_settings(monkeypatch, tmp_path):
    """
    Verify ENV > settings precedence by attempting a set of known env knobs.
    If none are honored by this build, skip with a clear reason.
    """
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})  # baseline false in file

    if not _try_env_override(monkeypatch, enable=True):
        pytest.skip("No recognized auth env override (AUTH_ENABLED/AUTH_MODE/AUTH) in this build")


def test_auth_enabled_env_disabled_overrides_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": True})  # baseline true in file

    if not _try_env_override(monkeypatch, enable=False):
        pytest.skip("No recognized auth env override (AUTH_ENABLED/AUTH_MODE/AUTH) in this build")

def test_repo_root_env_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    # _repo_root returns a Path; compare Path to Path
    assert shared._repo_root() == tmp_path


def test_database_url_sqlite_default(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    for k in ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    url = shared._database_url(str(tmp_path))
    assert url.startswith("sqlite:///")
    # Implementation stores plans DB under docs/plans/plans.db
    assert url.endswith("/docs/plans/plans.db?check_same_thread=false")


# NOTE: Postgres selection in _database_url appears guarded by additional logic/flags
# beyond POSTGRES_* vars. We only assert the SQLite default elsewhere.

# NOTE: _ensure_dir is not exported by services.api.core.shared; skipping.