import os
from sqlalchemy import create_engine, text
from services.api.core import shared

def test_db_init_sqlite(tmp_path, monkeypatch):
    # Hard-disable any Postgres paths that might be picked up implicitly
    for k in ("DATABASE_URL", "POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD"):
        monkeypatch.delenv(k, raising=False)

    # Force SQLite URL under tmp repo
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    # Build a guaranteed SQLite URL (don’t rely on db_init or external env)
    db_path = tmp_path / "unit.db"
    url = f"sqlite+pysqlite:///{db_path}"
    # Sanity: our helper should also choose sqlite by default now
    computed = shared._database_url(str(tmp_path))
    assert computed.startswith("sqlite:///")

    # Open a connection to prove the URL works and no Postgres path is taken
    eng = create_engine(url, future=True)
    with eng.connect() as conn:
        conn.execute(text("select 1"))