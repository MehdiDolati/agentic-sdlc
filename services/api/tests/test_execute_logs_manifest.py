from pathlib import Path
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def _repo_root() -> Path:
    # tests live at services/api/tests; we want the repo root
    return Path(__file__).resolve().parents[3]

def test_execute_creates_log_and_manifest_and_lists_artifacts():
    # 1) Plan it first
    r = client.post("/requests", json={"text": "Build a notes service with auth"})
    assert r.status_code == 200
    data = r.json()
    plan_id = data["plan_id"]
    prd_rel = data["artifacts"]["prd"]
    openapi_rel = data["artifacts"]["openapi"]

    # 2) Execute (runs inline during pytest)
    r = client.post(f"/plans/{plan_id}/execute")
    assert r.status_code == 202
    run_id = r.json()["run_id"]

    root = _repo_root() / "docs"
    run_dir = root / "plans" / plan_id / "runs" / run_id
    manifest_path = run_dir / "manifest.json"
    log_path = run_dir / "execution.log"

    # 3) Files exist
    assert run_dir.exists()
    assert manifest_path.exists()
    assert log_path.exists()

    # 4) Log is not empty and contains BEGIN/END markers
    log_text = log_path.read_text(encoding="utf-8")
    assert "BEGIN run" in log_text
    assert "END run" in log_text

    # 5) Manifest is correct and contains artifacts + log_path
    import json
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == run_id
    assert manifest["plan_id"] == plan_id
    assert manifest["log_path"].endswith(f"docs/plans/{plan_id}/runs/{run_id}/execution.log")

    # artifacts should include at least the PRD and OpenAPI paths
    arts = set(manifest.get("artifacts", []))
    assert prd_rel in arts
    assert openapi_rel in arts

def test_index_runs_array_is_appended_after_execute():
    # new plan
    r = client.post("/requests", json={"text": "Create a hello endpoint"})
    assert r.status_code == 200
    plan_id = r.json()["plan_id"]

    # exec
    r = client.post(f"/plans/{plan_id}/execute")
    assert r.status_code == 202
    run_id = r.json()["run_id"]

    # load index.json and verify the run pointer exists
    idx_path = _repo_root() / "docs" / "plans" / "index.json"
    import json
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    assert plan_id in idx
    runs = idx[plan_id].get("runs", [])
    assert any(r.get("run_id") == run_id for r in runs)
    # and that we recorded manifest/log paths
    run_entry = next(r for r in runs if r["run_id"] == run_id)
    assert run_entry["manifest_path"].endswith(f"docs/plans/{plan_id}/runs/{run_id}/manifest.json")
    assert run_entry["log_path"].endswith(f"docs/plans/{plan_id}/runs/{run_id}/execution.log")
