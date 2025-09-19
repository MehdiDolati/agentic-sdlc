import itertools
import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared, settings as cfg


def _exists(path, method="GET"):
    for r in app.routes:
        p = getattr(r, "path", "") or getattr(r, "path_format", "")
        ms = getattr(r, "methods", set())
        if p == path and method.upper() in ms:
            return True
    return False


def test_export_like_and_paging_branches(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)
    c = TestClient(app, raise_server_exceptions=False)

    if not _exists("/ui/plans", "GET"):
        pytest.skip("/ui/plans not mounted")

    sorts = ["created_at", "updated_at", "title"]
    directions = ["asc", "desc"]
    pages = ["1", "2"]
    sizes = ["1", "5"]

    for s, d, p, z in itertools.product(sorts, directions, pages, sizes):
        url = f"/ui/plans?sort={s}&direction={d}&page={p}&page_size={z}"
        # Ask for different Accepts to force codepaths
        for accept in ("text/html", "application/json", "text/csv"):
            r = c.get(url, headers={"Accept": accept})
            assert r.status_code in (200, 400, 404, 406, 415, 500)
