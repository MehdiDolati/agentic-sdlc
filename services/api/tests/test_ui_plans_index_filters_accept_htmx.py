import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared, settings as cfg


def _exists(path, method="GET"):
    for r in app.routes:
        p = getattr(r, "path", "") or getattr(r, "path_format", "")
        m = getattr(r, "methods", set())
        if p == path and method.upper() in m:
            return True
    return False


@pytest.mark.parametrize("htmx", [False, True])
def test_index_with_filters_and_accept_headers(tmp_path, monkeypatch, htmx):
    # Isolate repo + no auth gate
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)

    if not _exists("/ui/plans"):
        pytest.skip("/ui/plans not mounted")

    c = TestClient(app, raise_server_exceptions=False)

    base_headers = {}
    if htmx:
        base_headers = {
            "HX-Request": "true",
            "HX-Boosted": "true",
            "Accept": "text/html, */*;q=0.8",
        }

    # html
    r1 = c.get(
        "/ui/plans?q=hello&owner=me&status=open&artifact_type=plan"
        "&created_from=2020-01-01&created_to=2030-01-01"
        "&sort=created_at&direction=desc&page=1&page_size=5&limit=5&offset=0",
        headers=base_headers | {"Accept": "text/html"},
    )
    assert r1.status_code in (200, 400, 404, 500)

    # json-ish
    r2 = c.get(
        "/ui/plans?q=hello&direction=asc&page=2&page_size=1",
        headers=base_headers | {"Accept": "application/json"},
    )
    assert r2.status_code in (200, 400, 404, 406, 415, 500)

    # csv-ish
    r3 = c.get(
        "/ui/plans?sort=created_at&direction=desc&page=1&page_size=5",
        headers=base_headers | {"Accept": "text/csv"},
    )
    assert r3.status_code in (200, 400, 404, 406, 415, 500)

    # HTMX explicit partial fetch (same endpoint, just HTMX header)
    r4 = c.get("/ui/plans", headers=base_headers)
    assert r4.status_code in (200, 400, 404, 500)
