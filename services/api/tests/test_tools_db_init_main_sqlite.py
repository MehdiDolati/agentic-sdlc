import pytest
from services.api.core import shared

def test_db_init_main_sqlite(tmp_path, monkeypatch):
    # Force SQLite repo root; no PG env; import and run main([]) safely
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    for k in ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "DATABASE_URL"):
        monkeypatch.delenv(k, raising=False)
    import services.api.tools.db_init as mod
    main = getattr(mod, "main", None)
    if callable(main):
        main([])  # should be a no-op or create local files without hanging
    else:
        pytest.skip("db_init.main() not present")
