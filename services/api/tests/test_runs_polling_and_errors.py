import os
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared
from services.api.core.repos import PlansRepoDB, RunsRepoDB, ensure_plans_schema, ensure_runs_schema


def _setup_plan_and_run(tmp_path):
    """
    Seed a single plan and run in a temporary repository.
    Returns engine, plan_id and run_id.
    """
    os.environ["REPO_ROOT"] = str(tmp_path)
    shared._reset_repo_root_cache_for_tests()
    engine = shared._create_engine(shared._database_url(str(tmp_path)))
    ensure_plans_schema(engine)
    ensure_runs_schema(engine)
    plans = PlansRepoDB(engine)
    plan_id = "p123"
    plans.create({"id": plan_id, "request": "goal", "owner": "public", "artifacts": {}, "status": "new"})
    runs = RunsRepoDB(engine)
    run_id = "r123"
    runs.create(run_id, plan_id)
    return engine, plan_id, run_id


def test_run_fragment_and_404(tmp_path):
    """
    The run fragment should render the latest log lines and return 404 for missing runs
    or mismatched plan IDs.
    """
    engine, plan_id, run_id = _setup_plan_and_run(tmp_path)
    runs = RunsRepoDB(engine)
    # Assign paths and mark running
    log_rel = f"docs/plans/{plan_id}/runs/{run_id}/execution.log"
    manifest_rel = f"docs/plans/{plan_id}/runs/{run_id}/manifest.json"
    runs.set_running(run_id, manifest_rel, log_rel)

    # Write some log content
    log_path = (tmp_path / log_rel)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("hello\nworld", encoding="utf-8")

    # Retarget store for the test client
    _retarget_store(tmp_path)
    client = TestClient(app, raise_server_exceptions=False)

    # Fragment should include log contents
    resp = client.get(f"/ui/runs/{run_id}/fragment")
    assert resp.status_code == 200
    assert "hello" in resp.text and "world" in resp.text

    # Requesting an unknown run returns 404
    resp_missing = client.get("/ui/runs/missing")
    assert resp_missing.status_code == 404

    # Mismatched plan/run combination should return 404 via the plan-specific route
    resp_mismatch = client.get(f"/ui/plans/other/run/{run_id}")
    assert resp_mismatch.status_code == 404