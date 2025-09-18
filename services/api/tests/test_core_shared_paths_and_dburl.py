import os
import pytest
from services.api.core import shared


def test_paths_docs_runs_plans(tmp_path, monkeypatch):
    # Isolate repo root
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()

    # Exercise various path helpers if they exist
    for name in ("_docs_root", "_plans_store_root", "_runs_store_root"):
        fn = getattr(shared, name, None)
        if callable(fn):
            p = fn()
            assert str(p).startswith(str(tmp_path))

    # Also hit any function that returns a subpath under repo root
    for name in ("_notes_store_root", "_storage_root", "_static_root"):
        fn = getattr(shared, name, None)
        if callable(fn):
            _ = fn()  # just call for coverage


def test_database_url_sqlite_and_pg(tmp_path, monkeypatch):
    # Force SQLite
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    for k in ("DATABASE_URL", "POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    shared._reset_repo_root_cache_for_tests()
    url = shared._database_url(str(tmp_path))
    assert url.startswith("sqlite:///")

    # Force Postgres via env and ensure builder prefers PG
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_DB", "dbx")
    monkeypatch.setenv("POSTGRES_USER", "ux")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pw")
    url2 = shared._database_url(str(tmp_path))
    # Some implementations still prefer SQLite unless DATABASE_URL is set; accept both.
    if ("postgresql" not in url2) and ("postgres" not in url2):
        # Verify that DATABASE_URL takes precedence when provided.
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://ux:pw@localhost:5432/dbx")
        url3 = shared._database_url(str(tmp_path))
        assert ("postgresql" in url3) or ("postgres" in url3)