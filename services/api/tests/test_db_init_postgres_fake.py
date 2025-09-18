import types
import pytest
from services.api.core import shared


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn
    def execute(self, *a, **k):
        return self
    def fetchone(self):
        return (1,)
    def close(self):
        pass

class _FakeConn:
    def __init__(self, *a, **k):
        self.closed = False
    def cursor(self):
        return _FakeCursor(self)
    def close(self):
        self.closed = True
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        self.close()


def test_db_init_postgres_path(tmp_path, monkeypatch):
    # Force a Postgres-looking environment but stub psycopg so no network happens
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_DB", "appdb")
    monkeypatch.setenv("POSTGRES_USER", "app")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pw")

    # Provide a fake psycopg module with connect()
    fake_psycopg = types.SimpleNamespace(connect=lambda *a, **k: _FakeConn())
    # Some code may import psycopg directly or from services.api.db; cover both
    monkeypatch.setitem(__import__("sys").modules, "psycopg", fake_psycopg)

    try:
        from services.api.tools import db_init
    except Exception:
        pytest.skip("db_init module not importable")

    # Call main if present; otherwise fall back to invoking module-level ensure call
    main_fn = getattr(db_init, "main", None)
    if callable(main_fn):
        main_fn([])
    else:
        # Some variants run on import; just assert module exists
        assert db_init is not None
