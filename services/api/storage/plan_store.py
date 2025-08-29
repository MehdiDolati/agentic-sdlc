from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
import json
import tempfile
import uuid
from datetime import datetime, timezone

# Data file lives next to the API service code
_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_PLAN_FILE = _DATA_DIR / "plan.json"

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _read_store() -> Dict:
    if not _PLAN_FILE.exists():
        return {"plans": []}
    try:
        return json.loads(_PLAN_FILE.read_text(encoding="utf-8"))
    except Exception:
        # Corrupt or unreadable -> start fresh but do not blow up the API
        return {"plans": []}

def _write_store(store: Dict) -> None:
    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, dir=str(_DATA_DIR), encoding="utf-8") as fh:
            tmp = Path(fh.name)
            json.dump(store, fh, ensure_ascii=False, indent=2)
        tmp.replace(_PLAN_FILE)
    finally:
        if tmp and tmp.exists():
            try:
                tmp.unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                pass

def list_plans() -> List[Dict]:
    """
    Return a lightweight index for all plans:
    [{id, goal, created_at, updated_at, step_count, artifact_count}, ...]
    """
    store = _read_store()
    index = []
    for p in store.get("plans", []):
        steps = p.get("steps", []) or []
        artifacts = [a for s in steps for a in (s.get("artifacts") or [])]
        index.append({
            "id": p["id"],
            "goal": p.get("goal") or p.get("title") or "",
            "created_at": p.get("created_at"),
            "updated_at": p.get("updated_at"),
            "step_count": len(steps),
            "artifact_count": len(artifacts),
        })
    # Newest first
    index.sort(key=lambda x: (x.get("updated_at") or x.get("created_at") or ""), reverse=True)
    return index

def get_plan(plan_id: str) -> Optional[Dict]:
    store = _read_store()
    for p in store.get("plans", []):
        if p.get("id") == plan_id:
            return p
    return None

def upsert_plan(plan: Dict) -> Dict:
    """
    Insert new or replace existing plan by id. Adds timestamps if missing.
    Returns the stored plan dict.
    """
    store = _read_store()
    plans = store.setdefault("plans", [])

    now = _now_iso()
    if not plan.get("id"):
        plan["id"] = str(uuid.uuid4())
    if not plan.get("created_at"):
        plan["created_at"] = now
    plan["updated_at"] = now

    # Normalize steps/artifacts arrays
    for s in plan.setdefault("steps", []):
        s.setdefault("id", str(uuid.uuid4()))
        s.setdefault("status", "pending")
        s.setdefault("artifacts", [])
        if "created_at" not in s:
            s["created_at"] = now
        for a in s["artifacts"]:
            a.setdefault("id", str(uuid.uuid4()))
            if "created_at" not in a:
                a["created_at"] = now

    # Replace or append
    for i, existing in enumerate(plans):
        if existing.get("id") == plan["id"]:
            plans[i] = plan
            _write_store(store)
            return plan
    plans.append(plan)
    _write_store(store)
    return plan
