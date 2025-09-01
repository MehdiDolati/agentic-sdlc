from fastapi import APIRouter, BackgroundTasks
from pathlib import Path
import uuid, json, time, os

router = APIRouter()

def _repo_root():
    return Path(os.getcwd())

def _write_manifest(plan_id: str, run_id: str):
    repo_root = _repo_root()
    run_dir = repo_root / "docs" / "plans" / plan_id / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    log_path = run_dir / "execution.log"
    manifest_path = run_dir / "manifest.json"

    # --- write a simple execution log ---
    with log_path.open("a", encoding="utf-8") as lf:
        lf.write(f"[start] plan_id={plan_id} run_id={run_id}\n")
        lf.write("[done] execution complete\n")

    # --- try to fetch PRD/OpenAPI artifact paths from plans index ---
    artifacts_list = []
    idx_path = repo_root / "docs" / "plans" / "index.json"
    try:
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
        entry = idx.get(plan_id) or {}
        arts = entry.get("artifacts") or {}
        for k in ("prd", "openapi"):
            if k in arts:
                artifacts_list.append(arts[k])
    except FileNotFoundError:
        idx = {}

    completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # --- write manifest.json ---
    data = {
        "run_id": run_id,
        "plan_id": plan_id,
        "status": "completed",
        "completed_at": completed_at,
        "log_path": str(log_path.relative_to(repo_root)),
        "artifacts": artifacts_list,
    }
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # --- append run pointer into docs/plans/index.json ---
    entry = idx.get(plan_id) or {}
    runs = entry.get("runs") or []
    runs.append({
        "run_id": run_id,
        "manifest": str(manifest_path.relative_to(repo_root)),
        "created_at": completed_at,
    })
    entry["runs"] = runs
    idx[plan_id] = entry
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(json.dumps(idx, indent=2), encoding="utf-8")


@router.post("/plans/{plan_id}/execute", status_code=202)
def execute_plan(plan_id: str, background_tasks: BackgroundTasks):
    run_id = uuid.uuid4().hex[:8]
    background_tasks.add_task(_write_manifest, plan_id, run_id)
    return {"run_id": run_id}
