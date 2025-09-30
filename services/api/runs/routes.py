# services/api/runs/routes.py
from __future__ import annotations

import os
import time
import uuid
import json, threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import JSONResponse, PlainTextResponse

import services.api.core.shared as shared
from services.api.core.shared import (
    _database_url,
    _create_engine,
    _plans_index_path,    
    _load_index,
    _append_run_to_index,
    _auth_enabled,
)
from services.api.core.repos import PlansRepoDB, RunsRepoDB
from services.api.auth.routes import get_current_user  # reuse existing dependency

router = APIRouter(prefix="", tags=["runs"])

# --- helpers copied as-is from app.py (no behavior changes) ---
def _write_json(repo_root: Path, rel: str, data: dict) -> None:
    p = _ensure_parents(repo_root, rel)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")    

def _write_json(abs_path: Path, data: dict) -> None:
    _ensure_dir(abs_path.parent)
    abs_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _posix_rel(p: Path, root: Path) -> str:
    """Relative path as forward-slashes (stable across OS)."""
    return p.relative_to(root).as_posix()
    
def _docs_root(repo_root: Path) -> Path:
    # We’re standardizing all generated docs under services/docs
    return repo_root /  "docs"

def _plans_index_path(repo_root: Path) -> Path:
    return repo_root / "docs" / "plans" / "index.json"
    
def run_step(
    name: str,
    func: Callable[[Callable[[], bool]], Any],
    *,
    timeout_s: float = 5.0,
    retries: int = 0,
    backoff_s: float = 0.05,
    log_file: Path,
    cancel_file: Path
) -> Dict[str, Any]:
    """
    Run a single step with:
    - timeout per attempt
    - retry/backoff on failure/timeout
    - cooperative cancellation (func receives a should_cancel() callback)
    Returns a dict describing the step result.
    """
    result: Dict[str, Any] = {
        "name": name,
        "status": "unknown",
        "attempts": 0,
        "timed_out": False,
        "error": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "ended_at": None,
    }

    def should_cancel() -> bool:
        return cancel_file.exists()

    # thread wrapper to capture exceptions
    class Holder:
        exc: Optional[BaseException] = None

    attempts_allowed = retries + 1
    for attempt in range(1, attempts_allowed + 1):
        if should_cancel():
            result["status"] = "cancelled"
            result["attempts"] = attempt - 1
            result["ended_at"] = datetime.now(timezone.utc).isoformat()
            log_file.write_text(log_file.read_text(encoding="utf-8") + f"[{name}] cancelled before attempt {attempt}\n", encoding="utf-8")
            return result

        holder = Holder()

        def target():
            try:
                func(should_cancel)
            except BaseException as e:
                holder.exc = e

        t = threading.Thread(target=target, daemon=True)
        t.start()
        t.join(timeout_s)
        result["attempts"] = attempt

        if t.is_alive():
            # timeout
            result["timed_out"] = True
            # leave thread to die with the process; log and maybe retry
            log_file.write_text(log_file.read_text(encoding="utf-8") + f"[{name}] attempt {attempt} timed out after {timeout_s}s\n", encoding="utf-8")
            if attempt < attempts_allowed:
                time.sleep(backoff_s * (2 ** (attempt - 1)))
                continue
            else:
                result["status"] = "timeout"
                result["ended_at"] = datetime.now(timezone.utc).isoformat()
                return result

        # thread finished; inspect error or success
        if holder.exc is not None:
            log_file.write_text(log_file.read_text(encoding="utf-8") + f"[{name}] attempt {attempt} error: {holder.exc}\n", encoding="utf-8")
            if attempt < attempts_allowed:
                time.sleep(backoff_s * (2 ** (attempt - 1)))
                continue
            else:
                result["status"] = "error"
                result["error"] = str(holder.exc)
                result["ended_at"] = datetime.now(timezone.utc).isoformat()
                return result

        # success
        log_file.write_text(log_file.read_text(encoding="utf-8") + f"[{name}] attempt {attempt} ok\n", encoding="utf-8")
        result["status"] = "completed"
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        return result

    # Should not reach here
    result["status"] = "error"
    result["error"] = "Unexpected step runner state"
    result["ended_at"] = datetime.now(timezone.utc).isoformat()
    return result

class RunOut(BaseModel):
    id: str
    status: str
    manifest_path: Optional[str] = None
    log_path: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
# --------------------------------------------------------------------------------------
# Execute plan (background)
# --------------------------------------------------------------------------------------
def _run_plan(plan_id: str, run_id: str, repo_root: Path) -> None:
    """
    Execute a plan run and persist:
      - execution log: docs/plans/{plan_id}/runs/{run_id}/execution.log
      - manifest:      docs/plans/{plan_id}/runs/{run_id}/manifest.json
    Also append an entry under the plan's index with (run_id, log, manifest, status).
    Supports cancellation, per-step timeout, retry/backoff.
    """
    # Load index -> get plan entry
    idx = _load_index(repo_root)
    entry = idx.get(plan_id)
    if not entry:
        entry = {"id": plan_id, "artifacts": {}}
        idx[plan_id] = entry

    docs_root = _docs_root(repo_root)
    run_dir = docs_root / "plans" / plan_id / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    abs_log = run_dir / "execution.log"
    abs_manifest = run_dir / "manifest.json"
    cancel_flag = run_dir / "cancel.flag"

    # Begin log + initial 'running' manifest
    with abs_log.open("a", encoding="utf-8") as lf:
        lf.write(f"BEGIN run {run_id}\n")

    started = datetime.now(timezone.utc).isoformat()

    manifest: Dict[str, Any] = {
        "plan_id": plan_id,
        "run_id": run_id,
        "status": "running",
        "started_at": started,
        "log_path": _posix_rel(abs_log, repo_root),
        "artifacts": [],           # filled from index
        "steps": [],               # step results appended below
    }
    # include artifacts known at plan time
    arts = entry.get("artifacts") or {}
    # persist as posix rel
    for k in ["prd", "openapi", "adr", "stories", "tasks"]:
        if k in arts and arts[k]:
            manifest["artifacts"].append(arts[k])
    _write_json(abs_manifest, manifest)

    # define some "work" steps that regularly check for cancellation
    def _busy_step(duration_s: float, should_cancel: Callable[[], bool]):
        # do small sleeps so we can react to cancellation quickly
        t_end = time.time() + duration_s
        while time.time() < t_end:
            if should_cancel():
                return  # cooperatively stop
            time.sleep(0.01)

    # Three illustrative steps. Keep them short so tests remain fast.
    steps_spec = [
        ("prepare",   lambda sc: _busy_step(0.12, sc)),
        ("generate",  lambda sc: _busy_step(0.15, sc)),
        ("finalize",  lambda sc: _busy_step(0.10, sc)),
    ]

    overall_status = "completed"
    for name, fn in steps_spec:
        res = run_step(
            name,
            fn,
            timeout_s=2.0,
            retries=0,
            backoff_s=0.02,
            log_file=abs_log,
            cancel_file=cancel_flag,
        )
        manifest["steps"].append(res)
        # If cancelled/timeout/error: stop early and set final status
        if res["status"] == "cancelled":
            overall_status = "cancelled"
            break
        if res["status"] in ("timeout", "error"):
            overall_status = "failed"
            break

        # persist manifest after each step
        _write_json(abs_manifest, manifest)

    # finalize manifest/status
    manifest["status"] = overall_status
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(abs_manifest, manifest)

    with abs_log.open("a", encoding="utf-8") as lf:
        lf.write(f"END run {run_id}\n")

    # update index runs entry
    rel_manifest = _posix_rel(abs_manifest, repo_root)
    rel_log = _posix_rel(abs_log, repo_root)
    _append_run_to_index(repo_root, plan_id, run_id, rel_manifest, rel_log, overall_status)


def _bootstrap_running_manifest(repo_root: Path, plan_id: str, run_id: str) -> Dict[str, Any]:
    """
    Create/overwrite a 'running' manifest immediately so background tests can
    see status quickly.
    """
    docs_root = _docs_root(repo_root)  # your existing helper that returns repo_root / "docs"
    run_dir = docs_root / "plans" / plan_id / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = run_dir / "manifest.json"
    log_path      = run_dir / "execution.log"
    cancel_flag   = run_dir / "cancel.flag"

    now = datetime.now(timezone.utc).isoformat()
    manifest = {
        "plan_id": plan_id,
        "run_id": run_id,
        "status": "running",
        "started_at": now,
        "log_path": _posix_rel(log_path, repo_root),
        "artifacts": [],
        "steps": [],
    }
    _write_json(manifest_path, manifest)
    # ensure log file exists
    if not log_path.exists():
        log_path.write_text("", encoding="utf-8")
    # ensure cancel file does not exist at start
    if cancel_flag.exists():
        cancel_flag.unlink()
    return manifest

# --- routes ---

@router.post("/plans/{plan_id}/execute")
def _execute_plan_authed(
    plan_id: str,
    background: BackgroundTasks,
    background_mode: bool = Query(False, alias="background"),
    user: Dict[str, Any] = Depends(get_current_user),
):
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")
    repo_root = shared._repo_root()
    run_id = uuid.uuid4().hex[:8]

    if (os.getenv("CI") or os.getenv("PYTEST_CURRENT_TEST")) and not background_mode:
        _run_plan(plan_id, run_id, repo_root)
        return JSONResponse({"message": "Execution started", "run_id": run_id}, status_code=202)

    # background path
    _bootstrap_running_manifest(repo_root, plan_id, run_id)
    background.add_task(_run_plan, plan_id, run_id, repo_root)
    return JSONResponse({"message": "Execution started", "run_id": run_id}, status_code=202)

@router.get("/plans/{plan_id}/runs", response_model=list[RunOut])
def list_runs(plan_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")    
    engine = _create_engine(_database_url(shared._repo_root()))
    if not PlansRepoDB(engine).get(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    return RunsRepoDB(engine).list_for_plan(plan_id)


@router.get("/plans/{plan_id}/runs/{run_id}/manifest")
def get_run_manifest(plan_id: str, run_id: str):
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")
    repo_root = _repo_root()
    manifest_rel = f"docs/plans/{plan_id}/runs/{run_id}/manifest.json"
    p = Path(repo_root) / manifest_rel
    if not p.exists():
        raise HTTPException(status_code=404, detail="manifest not found")
    return json.loads(p.read_text(encoding="utf-8"))



@router.get("/plans/{plan_id}/runs/{run_id}/logs")
def get_run_logs(plan_id: str, run_id: str):
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")    
    repo_root = _repo_root()
    log_rel = f"docs/plans/{plan_id}/runs/{run_id}/log.ndjson"
    p = Path(repo_root) / log_rel
    if not p.exists():
        raise HTTPException(status_code=404, detail="log not found")
    # Return an array of events for test convenience
    events = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # skip malformed
                pass
    return {"events": events}
