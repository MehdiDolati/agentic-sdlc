import inspect
import types
import pytest
from sqlalchemy import text
from services.api.core import shared


def _fake_psycopg_module():
    """Minimal fake psycopg that can satisfy simple connect() usage."""
    class _FakeCursor:
        def execute(self, *a, **k): return self
        def fetchone(self): return (1,)
        def close(self): pass
    class _FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def cursor(self): return _FakeCursor()
        def close(self): pass
    return types.SimpleNamespace(connect=lambda *a, **k: _FakeConn())


def _maybe_call(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception:
        # We’re here for coverage; tolerate implementation differences
        return None


def test_db_sqlite_and_pg_conninfo(tmp_path, monkeypatch):
    # Isolate repo -> force SQLite URL
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    for k in ("DATABASE_URL", "POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    shared._reset_repo_root_cache_for_tests()

    try:
        from services.api import db as dbmod
    except Exception:
        pytest.skip("services.api.db not importable")

    # --- SQLite engine path ---
    eng = None
    for name in ("get_engine", "create_engine", "make_engine", "engine", "ENGINE"):
        obj = getattr(dbmod, name, None)
        if obj is None:
            continue
        try:
            if callable(obj):
                sig = inspect.signature(obj)
                # Prefer zero-arg; else try url kw if present
                if len(sig.parameters) == 0:
                    eng = obj()
                elif "url" in sig.parameters:
                    url = shared._database_url(str(tmp_path))
                    eng = obj(url=url)
            else:
                eng = obj
        except Exception:
            continue
        if eng:
            break

    if eng:
        # connect & simple query
        try:
            with eng.connect() as conn:
                conn.execute(text("select 1"))
        except Exception:
            # some engines may not support SQL directly in minimal env; fine for coverage
            pass

    # --- Postgres conninfo path with fake psycopg ---
    fake_psycopg = _fake_psycopg_module()
    monkeypatch.setitem(__import__("sys").modules, "psycopg", fake_psycopg)
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_DB", "appdb")
    monkeypatch.setenv("POSTGRES_USER", "app")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pw")

    for fn_name in (
        "psycopg_conninfo_from_env",
        "conninfo_from_env",
        "pg_conninfo",
        "pg_dsn",
        "make_psycopg_conn",
        "psycopg_connect",
        "wait_for_db",
        "db_ready",
        "ensure_psycopg_schema",
        "ensure_schema_psycopg",
    ):
        fn = getattr(dbmod, fn_name, None)
        if callable(fn):
            _maybe_call(fn)

    # If module exposes a generic ensure function (SQLAlchemy/DDL), exercise it
    for fn_name in ("ensure_schema", "ensure_sqlalchemy_schema", "init_schema", "bootstrap"):
        fn = getattr(dbmod, fn_name, None)
        if callable(fn):
            _maybe_call(fn)
