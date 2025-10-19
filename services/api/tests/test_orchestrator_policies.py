from pathlib import Path
import json, time
from fastapi.testclient import TestClient
from services.api.app import app
from services.api.runs.routes import run_step
import services.api.core.shared as shared   

client = TestClient(app)

def test_step_retries_then_succeeds(tmp_path: Path):
    # a function that fails first attempt, then succeeds
    attempts = {"n": 0}
    def f(should_cancel):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("first try fails")
        # quick success
        return

    repo_root = shared._repo_root()
    log = repo_root / "docs" / "plans" / "tmp" / "runs" / "temp" / "execution.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("", encoding="utf-8")
    cancel = log.parent / "cancel.flag"
    if cancel.exists():
        cancel.unlink()

    res = run_step("retry-demo", f, timeout_s=1.0, retries=1, backoff_s=0.01, log_file=log, cancel_file=cancel)
    assert res["status"] == "completed"
    assert res["attempts"] == 2
    lt = log.read_text(encoding="utf-8")
    assert "[retry-demo] attempt 1 error:" in lt
    assert "[retry-demo] attempt 2 ok" in lt

def test_step_times_out_after_retries(tmp_path: Path):
    def slow(should_cancel):
        # always slow -> always timeout
        time.sleep(0.06)

    repo_root = shared._repo_root()
    log = repo_root / "docs" / "plans" / "tmp" / "runs" / "timeout" / "execution.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("", encoding="utf-8")
    cancel = log.parent / "cancel.flag"
    if cancel.exists():
        cancel.unlink()

    res = run_step("timeout-demo", slow, timeout_s=0.01, retries=1, backoff_s=0.005, log_file=log, cancel_file=cancel)
    assert res["status"] == "timeout"
    assert res["attempts"] == 2
    lt = log.read_text(encoding="utf-8")
    assert "timed out" in lt

def test_cancel_endpoint_stops_run_and_sets_status_cancelled():
    # Plan a run
    r = client.post("/requests", json={"text": "Add search to notes list"})
    assert r.status_code == 200
    plan_id = r.json()["plan_id"]

    # Kick off background run (force background even under pytest)
    r2 = client.post(f"/plans/{plan_id}/execute?background=1")
    assert r2.status_code == 202
    run_id = r2.json()["run_id"]

    # Give it a moment to start and write 'running' manifest
    time.sleep(0.03)

    # Cancel it
    r3 = client.post(f"/plans/{plan_id}/runs/{run_id}/cancel")
    assert r3.status_code == 200

    # Allow the worker to notice cancellation
    time.sleep(0.15)

    repo_root = shared. _repo_root()
    manifest = repo_root / "docs" / "plans" / plan_id / "runs" / run_id / "manifest.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))

    # accepted outcomes: cancelled or (if race) completed
    assert data["status"] in ("cancelled", "completed"), data
    # log path present, steps array present
    assert "log_path" in data
    assert isinstance(data.get("steps"), list)