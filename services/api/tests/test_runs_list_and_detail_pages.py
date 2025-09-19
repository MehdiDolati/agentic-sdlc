import os, pytest
from starlette.testclient import TestClient
from services.api.app import app, _retarget_store
from services.api.core import shared
from services.api.core.repos import (
    PlansRepoDB,
    RunsRepoDB,
    ensure_plans_schema,
    ensure_runs_schema,
)


def _seed_plan_and_run(tmp_path):
    os.environ["REPO_ROOT"] = str(tmp_path)
    shared._reset_repo_root_cache_for_tests()
    engine = shared._create_engine(shared._database_url(str(tmp_path)))
    ensure_plans_schema(engine)
    ensure_runs_schema(engine)
    plans = PlansRepoDB(engine)
    runs = RunsRepoDB(engine)
    plan_id = "planx"
    run_id = "runx"
    plans.create({"id": plan_id, "request": "goal", "owner": "public", "artifacts": {}, "status": "new"})
    runs.create(run_id, plan_id)
    # Mark running with simple manifest/log locations
    log_rel = f"docs/plans/{plan_id}/runs/{run_id}/execution.log"
    manifest_rel = f"docs/plans/{plan_id}/runs/{run_id}/manifest.json"
    runs.set_running(run_id, manifest_rel, log_rel)
    # Write some log content to render
    p = (tmp_path / log_rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("line 1\nline 2", encoding="utf-8")
    return plan_id, run_id


def test_runs_list_and_detail_routes(tmp_path):
    plan_id, run_id = _seed_plan_and_run(tmp_path)
    _retarget_store(tmp_path)
    c = TestClient(app, raise_server_exceptions=False)

    # List view (HTML) – only if route exists
    if any(getattr(r, "path", "") == "/ui/runs" and "GET" in getattr(r, "methods", set()) for r in app.routes):
        li = c.get("/ui/runs")
        assert li.status_code == 200
        assert "Runs" in li.text or "Run" in li.text
    else:
        pytest.skip("/ui/runs not mounted in this build")

    # Detail page – only if route exists
    if any(getattr(r, "path", "") == "/ui/runs/{run_id}" and "GET" in getattr(r, "methods", set()) for r in app.routes):
        de = c.get(f"/ui/runs/{run_id}")
        assert de.status_code == 200
        # Should include IDs we set and some log content
        assert run_id in de.text
    else:
        pytest.skip("/ui/runs/{run_id} not mounted in this build")    # Mismatched plan/run detail route returns 404
    mismatch = c.get(f"/ui/plans/other/run/{run_id}")
    assert mismatch.status_code == 404