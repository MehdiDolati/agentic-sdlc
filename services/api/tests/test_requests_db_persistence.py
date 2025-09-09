from pathlib import Path
import json
from fastapi.testclient import TestClient
from services.api.app import app, _repo_root, _create_engine, _database_url, PlansRepoDB

def _register_and_login(client: TestClient, email: str, password: str) -> str:
    client.post("/auth/register", json={"email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]

def test_request_persists_in_db_and_not_plan_json(tmp_path: Path, monkeypatch):
    # point repo_root to a temp dir
    app.state.repo_root = str(tmp_path)

    client = TestClient(app)
    token = _register_and_login(client, "alice@example.com", "a")

    # create request
    r = client.post("/requests", json={"text": "Persistent DB plan"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    plan_id = body["plan_id"]
    assert plan_id

    # artifacts exist on disk
    repo_root = Path(_repo_root())
    for rel in body["artifacts"].values():
        assert (repo_root / rel).exists()

    # no plan.json file written (we keep only index.json for legacy APIs)
    plan_json = repo_root / "docs" / "plans" / plan_id / "plan.json"
    assert not plan_json.exists()

    # DB contains the plan (source of truth)
    engine = _create_engine(_database_url(repo_root))
    db_plan = PlansRepoDB(engine).get(plan_id)
    assert db_plan and db_plan["id"] == plan_id
    assert db_plan["request"] == "Persistent DB plan"
    assert db_plan["owner"].startswith("u_")  # from /auth/register

    # legacy index.json still updated to satisfy /plans list
    idx_path = repo_root / "docs" / "plans" / "index.json"
    assert idx_path.exists()
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    assert plan_id in idx
    assert idx[plan_id]["owner"] == db_plan["owner"]
