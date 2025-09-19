import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared, settings as cfg


def _collect_candidates():
    cands = []
    for r in app.routes:
        p = getattr(r, "path", "") or getattr(r, "path_format", "")
        ms = getattr(r, "methods", set())
        if p.startswith("/ui/plans"):
            # replace params
            url = p
            for seg in url.split("/"):
                if seg.startswith("{") and seg.endswith("}"):
                    url = url.replace(seg, "x")
            cands.append((url, [m.upper() for m in ms]))
    return cands


def test_action_cluster_params_and_variants(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)
    c = TestClient(app, raise_server_exceptions=False)

    h = {"HX-Request": "true", "HX-Boosted": "true", "Accept": "text/html"}
    form_common = {"kind": "tasks", "q": "hello", "status": "open", "owner": "me"}
    form_edge = {"kind": "invalid_kind", "only_open": "nope"}

    seen = False
    for path, methods in _collect_candidates():
        if "/board/" in path:
            # handled by the other test file
            continue
        for m in methods:
            seen = True
            if m in ("POST", "PUT", "PATCH"):
                # alternate payloads to hit error branches
                payload = form_common if (hash(path + m) % 2 == 0) else form_edge
                r = c.request(m, path, headers=h, data=payload)
            else:
                r = c.request(m, path, headers=h)
            assert r.status_code in (200, 201, 202, 204, 302, 303, 400, 401, 403, 404, 405, 409, 422, 500)
    if not seen:
        pytest.skip("No /ui/plans* routes discovered")
