import os
import uuid
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared
from services.api.core.repos import ensure_runs_schema, ensure_plans_schema


def test_notes_crud_happy_path(tmp_path):
    """
    Create a note, fetch it, list it (if supported), then delete it.
    """
    os.environ["REPO_ROOT"] = str(tmp_path)
    shared._reset_repo_root_cache_for_tests()
    _retarget_store(tmp_path)
    # Some installs may use DB-backed helpers; make sure tables exist if required.
    ensure_plans_schema(shared._create_engine(shared._database_url(str(tmp_path))))
    ensure_runs_schema(shared._create_engine(shared._database_url(str(tmp_path))))

    client = TestClient(app, raise_server_exceptions=False)

    # Create
    note_id = str(uuid.uuid4())[:8]
    create = client.post("/api/notes", json={"id": note_id, "text": "hello world"})
    assert create.status_code in (200, 201)
    body = create.json()
    assert body.get("id") == note_id
    assert body.get("text") == "hello world"

    # Get
    got = client.get(f"/api/notes/{note_id}")
    assert got.status_code == 200
    assert got.json()["text"] == "hello world"

    # Optional: list (if implemented) — don't fail if 404/not implemented
    listing = client.get("/api/notes")
    if listing.status_code == 200:
        j = listing.json()
        assert isinstance(j, list)
        # At least our note is somewhere in there
        assert any(x.get("id") == note_id for x in j)

    # Delete
    deleted = client.delete(f"/api/notes/{note_id}")
    assert deleted.status_code in (200, 204)

    # Now 404 on get
    missing = client.get(f"/api/notes/{note_id}")
    assert missing.status_code == 404


def test_notes_404s(tmp_path):
    _retarget_store(tmp_path)
    client = TestClient(app, raise_server_exceptions=False)
    # Deleting a non-existent note should 404 (or 204 in some builds; accept both)
    resp = client.delete("/api/notes/nope")
    assert resp.status_code in (204, 404)