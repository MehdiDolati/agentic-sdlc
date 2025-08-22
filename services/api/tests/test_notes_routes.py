
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_notes_crud_flow():
    r = client.get("/api/notes", headers={"Authorization": "Bearer test"})
    assert r.status_code == 200
    assert r.json() == []

    r = client.post("/api/notes", headers={"Authorization": "Bearer test"}, json={"title": "t", "content": "c"})
    assert r.status_code == 201
    created = r.json()
    _id = created["id"]

    r = client.get(f"/api/notes/{_id}", headers={"Authorization": "Bearer test"})
    assert r.status_code == 200
    assert r.json()["title"] == "t"

    r = client.put(f"/api/notes/{_id}", headers={"Authorization": "Bearer test"}, json={"title": "t2", "content": "c2"})
    assert r.status_code == 200
    assert r.json()["title"] == "t2"

    r = client.delete(f"/api/notes/{_id}", headers={"Authorization": "Bearer test"})
    assert r.status_code == 204

    r = client.get(f"/api/notes/{_id}", headers={"Authorization": "Bearer test"})
    assert r.status_code == 404
