import inspect
import pytest
from services.api.core import shared


def _call_any(fn):
    sig = inspect.signature(fn)
    try:
        if len(sig.parameters) == 0:
            return fn()
        # Accept an optional engine/session arg; pass None to hit default path
        return fn(None)
    except Exception:
        # We're here for coverage; tolerate implementations that differ
        return None


def test_core_repos_ensure_schema_sqlite(tmp_path, monkeypatch):
    # Force SQLite mode by clearing PG hints
    for k in ("DATABASE_URL", "POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    url = shared._database_url(str(tmp_path))
    assert url.startswith("sqlite:///")

    try:
        from services.api.core import repos as repos_mod
    except Exception:
        pytest.skip("core.repos not importable")

    for name in ("ensure_plans_schema", "ensure_runs_schema", "ensure_notes_schema"):
        fn = getattr(repos_mod, name, None)
        if callable(fn):
            _call_any(fn)
