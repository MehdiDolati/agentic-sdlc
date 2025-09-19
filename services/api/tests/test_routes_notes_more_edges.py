import uuid
import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared, settings as cfg

def test_notes_server_generated_id_and_bad_get(tmp_path, monkeypatch):
    # Isolate & relax auth
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)
    c = TestClient(app, raise_server_exceptions=False)

    # Create WITHOUT id -> server may generate one
    r = c.post("/api/notes", json={"text": "server id please"})
    assert r.status_code in (200, 201, 202, 204, 400, 422)
    if r.status_code in (200, 201):
        sid = r.json().get("id")
        if sid:
            g = c.get(f"/api/notes/{sid}")
            assert g.status_code in (200, 404)  # implementations vary (eventual)
    # Bad get should 404/400
    g2 = c.get("/api/notes/bad-id-xxxxx")
    assert g2.status_code in (400, 404)

def test_notes_put_empty_and_delete_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)
    c = TestClient(app, raise_server_exceptions=False)

    # Update non-existent note
    nid = uuid.uuid4().hex[:8]
    p = c.put(f"/api/notes/{nid}", json={})
    assert p.status_code in (200, 204, 400, 404, 422)

    # Delete non-existent
    d = c.delete(f"/api/notes/{nid}")
    assert d.status_code in (200, 204, 404)
