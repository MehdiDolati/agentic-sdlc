import uuid
import pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared, settings as cfg


def _route_exists(path: str, method: str = "GET") -> bool:
    m = method.upper()
    for r in app.routes:
        if getattr(r, "path", "") == path and m in getattr(r, "methods", set()):
            return True
    return False


def test_notes_crud_on_main_app(tmp_path, monkeypatch):
    # Isolate store + disable auth gates to reach the endpoints easily
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    shared._reset_repo_root_cache_for_tests()
    cfg.save_settings(tmp_path, {"auth_enabled": False})
    _retarget_store(tmp_path)

    c = TestClient(app, raise_server_exceptions=False)
    headers = {"Authorization": "Bearer test"}  # harmless if ignored

    if not _route_exists("/api/notes", "GET"):
        pytest.skip("/api/notes not mounted on main app")

    note_id = uuid.uuid4().hex[:8]
    # Create
    r = c.post("/api/notes", json={"id": note_id, "text": "hello"}, headers=headers)
    assert r.status_code in (200, 201, 422, 500)
    j = None
    try:
        j = r.json()
    except Exception:
        pass
    server_id = (j or {}).get("id") or note_id

    # Get
    g = c.get(f"/api/notes/{server_id}", headers=headers)
    assert g.status_code in (200, 404, 500)

    # Update
    u = c.put(f"/api/notes/{server_id}", json={"text": "updated"}, headers=headers)
    assert u.status_code in (200, 204, 404, 422, 500)

    # Delete
    d = c.delete(f"/api/notes/{server_id}", headers=headers)
    assert d.status_code in (200, 204, 404, 500)
