# services/api/tests/test_plans_pagination_filters.py
from services.api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)

def _mk(text):
    r = client.post("/requests", json={"text": text})
    assert r.status_code == 200
    return r.json()["plan_id"]

def test_plans_pagination_and_filtering():
    # Create a few plans
    a = _mk("Build a notes service with auth")
    b = _mk("Create a hello endpoint")
    c = _mk("Add search to notes list")

    # Basic list
    r = client.get("/plans")
    assert r.status_code == 200
    data = r.json()
    assert "plans" in data and isinstance(data["plans"], list)
    assert "total" in data and data["total"] >= 3

    # limit
    r = client.get("/plans?limit=2")
    j = r.json()
    assert j["limit"] == 2
    assert len(j["plans"]) == 2
    assert j["total"] >= 3

    # offset
    r2 = client.get("/plans?offset=2&limit=2")
    j2 = r2.json()
    assert j2["offset"] == 2
    # total stays same; page count may be 1+ depending on how many exist
    assert j2["total"] == j["total"]

    # filter by substring (case-insensitive in request or id)
    r = client.get("/plans?q=notes")
    jf = r.json()
    assert all(
        ("notes" in p["request"].lower()) or ("notes" in p["id"].lower())
        for p in jf["plans"]
    )
    assert jf["total"] <= data["total"]
