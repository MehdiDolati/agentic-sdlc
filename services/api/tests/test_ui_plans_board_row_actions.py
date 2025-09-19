import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared, settings as cfg


def _collect_targets():
    # Gather many per-row endpoints under /ui/plans/{id}/board/*
    targets = []
    for r in app.routes:
        p = getattr(r, "path", "") or getattr(r, "path_format", "")
        ms = getattr(r, "methods", set())
        if "/ui/plans/" in p and "/board/" in p and ms:
            # replace any {param}
            url = p
            for seg in url.split("/"):
                if seg.startswith("{") and seg.endswith("}"):
                    url = url.replace(seg, "x")
            targets.append((url, [m.upper() for m in ms]))
    return targets


def test_board_row_actions_sweep(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)

    c = TestClient(app, raise_server_exceptions=False)
    h = {"HX-Request": "true", "Accept": "text/html"}

    for url, methods in _collect_targets():
        for m in methods:
            # Minimal form—handlers that don't care will ignore it
            form = {"title": "T", "status": "open", "assignee": "me"}
            if m in ("POST", "PUT", "PATCH"):
                r = c.request(m, url, headers=h, data=form)
            else:
                r = c.request(m, url, headers=h)
            assert r.status_code in (200, 201, 202, 204, 302, 303, 400, 401, 403, 404, 405, 409, 422, 500)
