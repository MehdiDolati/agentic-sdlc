from fastapi.testclient import TestClient
from services.api.app import app

client = TestClient(app)
HDR = {"Authorization": "Bearer test"}

def test_notes_crud_flow():
    r = client.get("/api/notes", headers=HDR)
    assert r.status_code == 200
    assert r.json() == []

    r = client.post("/api/notes", headers=HDR, json={"title": "t", "content": "c"})
    assert r.status_code == 201
    created = r.json()
    _id = created["id"]

    r = client.get("/api/notes/" + _id, headers=HDR)
    assert r.status_code == 200
    assert r.json()["title"] == "t"

    r = client.put("/api/notes/" + _id, headers=HDR, json={"title": "t2", "content": "c2"})
    assert r.status_code == 200
    assert r.json()["title"] == "t2"

    r = client.delete("/api/notes/" + _id, headers=HDR)
    assert r.status_code == 204

    r = client.get("/api/notes/" + _id, headers=HDR)
    assert r.status_code == 404
