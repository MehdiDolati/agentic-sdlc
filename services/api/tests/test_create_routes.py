from fastapi.testclient import TestClient
from services.api.app import app

client = TestClient(app)

def test_create_crud_flow():
    r = client.get("/api/create")
    assert r.status_code == 200
    assert r.json() == []

    r = client.post("/api/create", json={"title": "t", "content": "c"})
    assert r.status_code == 201
    created = r.json()
    _id = created["id"]

    r = client.get("/api/create/" + _id)
    assert r.status_code == 200
    assert r.json()["title"] == "t"

    r = client.put("/api/create/" + _id, json={"title": "t2", "content": "c2"})
    assert r.status_code == 200
    assert r.json()["title"] == "t2"

    r = client.delete("/api/create/" + _id)
    assert r.status_code == 204

    r = client.get("/api/create/" + _id)
    assert r.status_code == 404
