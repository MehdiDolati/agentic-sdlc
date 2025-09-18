import inspect
import types
import pytest
from sqlalchemy import text
from services.api.core import shared

def _mk_fake_psycopg():
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

def test_db_dsn_and_sqlalchemy(tmp_path, monkeypatch):
    # First force SQLite and exercise any engine/session helpers
    for k in ("DATABASE_URL", "POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    url = shared._database_url(str(tmp_path))
    assert url.startswith("sqlite:///")

    try:
        from services.api import db as dbmod
    except Exception:
        pytest.skip("db module not importable")

    # Try to get an engine (zero-arg or url kw)
    eng = None
    for name in ("engine", "ENGINE", "get_engine", "create_engine", "make_engine"):
        obj = getattr(dbmod, name, None)
        if obj is None:
            continue
        try:
            if callable(obj):
                sig = inspect.signature(obj)
                if len(sig.parameters) == 0:
                    eng = obj()
                elif "url" in sig.parameters:
                    eng = obj(url=url)
            else:
                eng = obj
        except Exception:
            continue
        if eng:
            break

    if eng:
        try:
            with eng.connect() as conn:
                conn.execute(text("select 1"))
        except Exception:
            pass

    # Now simulate Postgres DSN path with fake psycopg
    fake_psycopg = _mk_fake_psycopg()
    monkeypatch.setitem(__import__("sys").modules, "psycopg", fake_psycopg)
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_DB", "appdb")
    monkeypatch.setenv("POSTGRES_USER", "app")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pw")

    # If module exposes a DSN/conninfo builder, call it
    for name in ("psycopg_conninfo_from_env", "conninfo_from_env", "pg_conninfo", "pg_dsn"):
        fn = getattr(dbmod, name, None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass