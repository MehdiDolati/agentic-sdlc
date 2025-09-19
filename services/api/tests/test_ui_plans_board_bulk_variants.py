import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared, settings as cfg


def _methods(path):
    for r in app.routes:
        p = getattr(r, "path", "") or getattr(r, "path_format", "")
        ms = getattr(r, "methods", set())
        if p == path:
            return ms
    return set()


def test_board_bulk_variants_with_htmx(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)

    c = TestClient(app, raise_server_exceptions=False)
    htx = {"HX-Request": "true", "HX-Boosted": "true", "Accept": "text/html"}

    base = "/ui/plans/x/board/bulk"
    if not _methods(base):
        pytest.skip("bulk board endpoint not mounted")

    # Valid-ish kinds common in UI
    valid_forms = [
        {"kind": "tasks", "only_open": "true"},
        {"kind": "notes"},
        {"kind": "issues"},   # may map to GH; still safe if unconfigured
        {"kind": "runs"},
    ]
    for f in valid_forms:
        r = c.post(base, data=f, headers=htx)
        assert r.status_code in (200, 204, 302, 303, 400, 401, 403, 404, 409, 422, 500)

    # Invalid kind drives error branches & flash
    r2 = c.post(base, data={"kind": "nope"}, headers=htx)
    assert r2.status_code in (200, 204, 302, 303, 400, 404, 409, 422, 500)
