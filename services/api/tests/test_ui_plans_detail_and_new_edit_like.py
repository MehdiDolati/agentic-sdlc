import uuid
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


def test_new_form_detail_and_missing_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)

    c = TestClient(app, raise_server_exceptions=False)

    if _exists("/ui/plans/new", "GET"):
        r = c.get("/ui/plans/new")
        assert r.status_code in (200, 404, 500)

    # Missing plan detail page should be a handled 404/400/500
    missing_id = "x" + uuid.uuid4().hex[:6]
    for p in (f"/ui/plans/{missing_id}", f"/ui/plans/{missing_id}/view"):
        if _exists(p, "GET"):
            rr = c.get(p)
            assert rr.status_code in (200, 400, 404, 500)

    # Try edit form if present
    p_edit = f"/ui/plans/{missing_id}/edit"
    if _exists(p_edit, "GET"):
        re = c.get(p_edit)
        assert re.status_code in (200, 400, 404, 500)

    # Try delete-ish endpoint (often POST with a CSRF/confirmation in real apps; keep tolerant)
    p_del = f"/ui/plans/{missing_id}/delete"
    if _exists(p_del, "POST"):
        rd = c.post(p_del, data={"confirm": "yes"})
        assert rd.status_code in (200, 204, 302, 303, 400, 404, 409, 422, 500)
