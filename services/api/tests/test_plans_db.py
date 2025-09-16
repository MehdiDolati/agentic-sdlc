from pathlib import Path
import importlib
from fastapi.testclient import TestClient
from services.api.core.repos import PlansRepoDB

def _setup_app(tmp_path: Path):
    import app as app_module
    importlib.reload(app_module)
    app_module._repo_root = lambda: tmp_path  # point everything to temp repo root
    return app_module.app, app_module

def test_create_request_persists_plan_in_db(tmp_path: Path, monkeypatch, repo_root):
    # signal deterministic paths & non-LLM fallback paths
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    app, app_module = _setup_app(tmp_path)
    client = TestClient(app)

    # create a plan
    r = client.post("/requests", json={"text": "DB persistence smoke"})
    assert r.status_code == 200
    j = r.json()
    plan_id = j["plan_id"]

    # verify artifacts written to disk
    arts = j["artifacts"]
    assert (tmp_path / arts["prd"]).exists()
    assert (tmp_path / arts["openapi"]).exists()

    # verify plan row in DB
    engine = app_module._create_engine(app_module._database_url(tmp_path))
    repo = app_module.PlansRepoDB(engine)
    plan = repo.get(plan_id)
    assert plan is not None
    assert plan["request"] == "DB persistence smoke"
    assert "prd" in plan["artifacts"]
    assert "openapi" in plan["artifacts"]

    # UI list uses DB
    r = client.get("/ui/plans")
    assert r.status_code == 200
    assert "Plans" in r.text
    assert "DB persistence smoke" in r.text

    # UI detail uses DB
    r = client.get(f"/ui/plans/{plan_id}")
    assert r.status_code == 200
    assert "DB persistence smoke" in r.text
    # The sections still render from disk artifacts
    assert "<h2>PRD</h2>" in r.text
    assert "<h2>OpenAPI</h2>" in r.text

def test_plans_repo_update_artifacts(tmp_path):
    app, app_module = _setup_app(tmp_path)
    engine = app_module._create_engine(app_module._database_url(tmp_path))
    repo = PlansRepoDB(engine)
    repo.create({"id":"p1","request":"r","owner":"ui","artifacts":{},"status":"new"})
    out = repo.update_artifacts("p1", {"prd":"docs/prd/PRD-p1.md"})
    assert out["artifacts"]["prd"].endswith("PRD-p1.md")
    out2 = repo.update("p1", {"status":"running"})
    assert out2["status"] == "running"
