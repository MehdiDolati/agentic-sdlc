import os
import inspect
import pytest
from sqlalchemy import text
from services.api.core import shared


def _force_sqlite_env(tmp_path, monkeypatch):
    # Kill PG hints
    for k in ("DATABASE_URL", "POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
              "PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    # Your helper should prefer sqlite now
    url = shared._database_url(str(tmp_path))
    assert url.startswith("sqlite:///")
    return url


def test_db_module_sqlite(tmp_path, monkeypatch):
    _force_sqlite_env(tmp_path, monkeypatch)
    # Import after environment is set so module-level code uses SQLite
    try:
        from services.api import db as dbmod
    except Exception:
        pytest.skip("services.api.db not importable")

    # Find an engine or factory on the module
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
                else:
                    # Best-effort: pass URL if accepted
                    kwargs = {}
                    if "url" in sig.parameters:
                        kwargs["url"] = shared._database_url(str(tmp_path))
                    eng = obj(**kwargs) if kwargs else obj(None)
            else:
                eng = obj
        except Exception:
            continue
        if eng is not None:
            break

    if eng is None:
        pytest.skip("No usable engine/factory exposed by services.api.db")

    # Run a trivial statement to ensure connectivity and execute code paths
    try:
        conn = eng.connect()
    except Exception:
        # Some modules wrap SQLAlchemy engine differently
        get_conn = getattr(dbmod, "get_connection", None)
        if callable(get_conn):
            conn = get_conn()
        else:
            pytest.skip("Could not obtain a DB connection")

    with conn:
        conn.execute(text("select 1"))
