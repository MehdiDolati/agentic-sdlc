from fastapi import APIRouter, BackgroundTasks
from pathlib import Path
import uuid, json, time, os

router = APIRouter()

def _repo_root():
    return Path(os.getcwd())

def _write_manifest(plan_id: str, run_id: str):
    run_dir = _repo_root() / "docs" / "plans" / plan_id / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = run_dir / "manifest.json"
    # Simulate "completed" execution
    data = {
        "run_id": run_id,
        "plan_id": plan_id,
        "status": "completed",
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    manifest.write_text(json.dumps(data, indent=2))

@router.post("/plans/{plan_id}/execute", status_code=202)
def execute_plan(plan_id: str, background_tasks: BackgroundTasks):
    run_id = uuid.uuid4().hex[:8]
    background_tasks.add_task(_write_manifest, plan_id, run_id)
    return {"run_id": run_id}
