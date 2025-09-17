import os
import pytest
from services.api.core import shared
from services.api.core import settings as cfg


def test_auth_enabled_env_overrides_settings(monkeypatch, tmp_path):
    """
    AUTH_ENABLED (or AUTH_MODE) in the environment should take precedence over the persisted settings file.
    """
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()

    # Persist auth_enabled = True in settings.json
    cfg.save_settings(tmp_path, {"auth_enabled": True})

    # Environment says "false" -> gate disabled
    monkeypatch.setenv("AUTH_ENABLED", "false")
    assert shared._auth_enabled() is False

    # Environment says "yes" -> gate enabled
    monkeypatch.setenv("AUTH_ENABLED", "yes")
    assert shared._auth_enabled() is True


def test_auth_enabled_settings_no_env(monkeypatch, tmp_path):
    """
    When no override is present, the value is read from the settings file.
    """
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()

    # Explicitly enable in settings
    cfg.save_settings(tmp_path, {"auth_enabled": True})
    monkeypatch.delenv("AUTH_ENABLED", raising=False)
    monkeypatch.delenv("AUTH_MODE", raising=False)
    assert shared._auth_enabled() is True

    # Explicitly disable in settings
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    assert shared._auth_enabled() is False


def test_auth_enabled_defaults(monkeypatch, tmp_path):
    """
    Without a settings file and no env override, auth defaults to disabled.
    """
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    monkeypatch.delenv("AUTH_ENABLED", raising=False)
    monkeypatch.delenv("AUTH_MODE", raising=False)
    assert shared._auth_enabled() is False
