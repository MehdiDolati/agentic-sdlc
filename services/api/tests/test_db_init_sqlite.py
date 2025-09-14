from __future__ import annotations
import importlib
import sys
from pathlib import Path

def test_db_init_skips_wait_on_sqlite(tmp_path, monkeypatch, capsys):
    # Arrange: SQLite DSN (like we use in the container for dev)
    monkeypatch.setenv("DATABASE_URL", "sqlite:////" + str(tmp_path / "docs" / "plans" / "plans.db"))
    # Make sure we're importing a fresh module each time
    if "services.api.tools.db_init" in sys.modules:
        del sys.modules["services.api.tools.db_init"]
    import services.api.tools.db_init as db_init

    # Act: run() should return quickly and print the sqlite message
    db_init.run()
    out = capsys.readouterr().out
    assert "sqlite detected" in out.lower()

def test_db_init_connects_when_postgres_available(monkeypatch, capsys):
    """
    We don't spin up a real Postgres here; we stub psycopg.connect to succeed once.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:app@db:5432/appdb")
    # Fresh import
    for m in list(sys.modules):
        if m.startswith("services.api.tools.db_init"):
            del sys.modules[m]
    import services.api.tools.db_init as db_init

    class _FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def cursor(self): return self
        def execute(self, *a, **kw): return None
        def commit(self): return None

    class _FakePsycopg:
        def connect(self, dsn): return _FakeConn()

    # Stub psycopg in the module namespace
    monkeypatch.setitem(sys.modules, "psycopg", _FakePsycopg())

    db_init.run()
    out = capsys.readouterr().out
    assert "database ready" in out.lower()
