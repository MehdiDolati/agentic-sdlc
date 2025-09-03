from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_notes_crud_db_backed():
    # Create
    r = client.post("/api/notes", json={"text": "hello db!"})
    assert r.status_code == 201
    created = r.json()
    nid = created["id"]
    assert created["text"] == "hello db!"

    # List
    r = client.get("/api/notes")
    assert r.status_code == 200
    items = r.json()
    assert any(n["id"] == nid and n.get("text") == "hello db!" for n in items)

    # Get one
    r = client.get(f"/api/notes/{nid}")
    assert r.status_code == 200
    assert r.json().get("text") == "hello db!"

    # Update
    r = client.put(f"/api/notes/{nid}", json={"text": "updated!"})
    assert r.status_code == 200
    assert r.json().get("text") == "updated!"

    # Delete
    r = client.delete(f"/api/notes/{nid}")
    assert r.status_code == 204

    # 404 after delete
    r = client.get(f"/api/notes/{nid}")
    assert r.status_code == 404
