# REMOVE these top-level imports:
# from services.api.app import app, _repo_root, _create_engine, _database_url, PlansRepoDB

from pathlib import Path
import json
from fastapi.testclient import TestClient
import importlib

def _register_and_login(client: TestClient, email: str, password: str) -> str:
    client.post("/auth/register", json={"email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]

def test_request_persists_in_db_and_not_plan_json(tmp_path: Path, monkeypatch):
    # 1) Point the app to THIS test's repo root via env
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)  # ensure sqlite path is used

    # 2) Reload shared first (drops cached _repo_root), then app
    import services.api.core.shared as shared
    importlib.reload(shared)
    import services.api.app as app_module
    importlib.reload(app_module)

    # 3) Now build client from the reloaded app
    client = TestClient(app_module.app)
    token = _register_and_login(client, "alice@example.com", "a")

    # 4) Create request
    r = client.post(
        "/requests",
        json={"text": "Persistent DB plan"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    plan_id = body["plan_id"]
    assert plan_id

    # 5) Assert artifacts under the SAME repo root this test set
    repo_root = Path(shared._repo_root())
    for rel in body["artifacts"].values():
        assert (repo_root / rel).exists()

    # 6) No per-plan JSON
    plan_json = repo_root / "docs" / "plans" / plan_id / "plan.json"
    assert not plan_json.exists()

    # 7) DB contains the plan (use the SAME shared helpers)
    engine = shared._create_engine(shared._database_url(repo_root))
    db_plan = app_module.PlansRepoDB(engine).get(plan_id)
    assert db_plan and db_plan["id"] == plan_id
    assert db_plan["request"] == "Persistent DB plan"
    assert db_plan["owner"].startswith("u_")

    # 8) legacy index.json updated
    idx_path = repo_root / "docs" / "plans" / "index.json"
    assert idx_path.exists()
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    assert plan_id in idx
    assert idx[plan_id]["owner"] == db_plan["owner"]
