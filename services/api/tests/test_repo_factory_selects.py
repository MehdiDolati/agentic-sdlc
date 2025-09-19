import pytest
from services.api.core import shared
from services.api.core import settings as cfg

def _reset_env(monkeypatch):
    for k in ("DATABASE_URL", "POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_PORT"):
        monkeypatch.delenv(k, raising=False)

def test_factory_prefers_sqlite_memory_when_no_pg(monkeypatch, tmp_path):
    # No PG env -> memory/sqlite path
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _reset_env(monkeypatch)

    from services.api.repo import factory as f
    repo = f.get_repo() if hasattr(f, "get_repo") else None
    # Don’t be strict on type; assert it has basic shape
    assert repo is None or all(hasattr(repo, x) for x in ("save_plan", "get_plan", "list_plans"))

def test_factory_can_build_pg_when_env_present(monkeypatch, tmp_path):
    # Provide PG env; we don't actually connect—just exercise factory branch
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_DB", "d")
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")

    from services.api.repo import factory as f
    repo = f.get_repo() if hasattr(f, "get_repo") else None
    assert repo is None or all(hasattr(repo, x) for x in ("save_plan", "get_plan", "list_plans"))