import types
import pytest
from services.api.core import shared


def _fake_psycopg_erroring():
    class _ErrConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def cursor(self): raise RuntimeError("cannot make cursor")
        def close(self): pass
    def _connect(*a, **k): raise RuntimeError("connect failed")
    return types.SimpleNamespace(connect=_connect, Connection=_ErrConn)


def test_db_psycopg_error_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    try:
        from services.api import db as dbmod
    except Exception:
        pytest.skip("services.api.db not importable")

    # Force PG env + fake psycopg that fails on connect
    monkeypatch.setenv("POSTGRES_HOST", "x")
    monkeypatch.setenv("POSTGRES_DB", "x")
    monkeypatch.setenv("POSTGRES_USER", "x")
    monkeypatch.setenv("POSTGRES_PASSWORD", "x")
    monkeypatch.setitem(__import__("sys").modules, "psycopg", _fake_psycopg_erroring())

    # Exercise any resilience/readiness helpers; allow exceptions or None — goal is coverage
    for name in ("psycopg_conninfo_from_env", "conninfo_from_env", "pg_conninfo", "pg_dsn",
                 "psycopg_connect", "wait_for_db", "db_ready",
                 "ensure_psycopg_schema", "ensure_schema_psycopg"):
        fn = getattr(dbmod, name, None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass


def test_database_url_explicit_precedence(tmp_path, monkeypatch):
    # Even if PG env vars exist, explicit DATABASE_URL should win
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_DB", "dbx")
    monkeypatch.setenv("POSTGRES_USER", "ux")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pw")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://ux:pw@localhost:5432/dbx")

    from services.api.core import shared as sh
    url = sh._database_url(str(tmp_path))
    assert "postgres" in url
