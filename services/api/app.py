# services/api/app.py
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import json
import uuid  # <-- add this


# --- Ensure both repo root and services/api are on sys.path for CI/pytest ---
from pathlib import Path
import sys

API_DIR = Path(__file__).resolve().parent          # .../services/api
ROOT    = API_DIR.parent.parent                    # repo root
for p in (str(API_DIR), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

# --- planner (static, no importlib) ---
try:
    from .planner import plan_request              # package context (uvicorn)
except Exception:
    try:
        from services.api.planner import plan_request  # absolute package
    except Exception:
        from planner import plan_request           # top-level (pytest from repo root)

# --- routers (static, no importlib) ---
try:
    from .routes.create import router as create_router
    from .routes.notes  import router as notes_router
except Exception:
    # top-level fallback (pytest from repo root with API_DIR on sys.path)
    from routes.create import router as create_router
    from routes.notes  import router as notes_router

app = FastAPI(title="Agentic SDLC API", version="0.5.0")
app.include_router(create_router)
app.include_router(notes_router)

class RequestIn(BaseModel):
    text: str
    
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _plans_index_path(repo_root: Path) -> Path:
    p = repo_root / "docs" / "plans" / "index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("{}", encoding="utf-8")
    return p

def _load_index(repo_root: Path) -> dict:
    p = _plans_index_path(repo_root)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

def _save_index(repo_root: Path, data: dict) -> None:
    p = _plans_index_path(repo_root)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def _slugify(text: str) -> str:
    import re
    t = (text or "").lower().strip()
    t = re.sub(r'[^a-z0-9\s-]', '', t)
    t = re.sub(r'[\s-]+', '-', t).strip('-')
    return t[:60] or "request"

app.include_router(create_router)

app.include_router(notes_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/requests")
def create_request(req: RequestIn):
    repo_root = _repo_root()
    artifacts = plan_request(req.text, repo_root)

    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    plan_id = f"{ts}-{_slugify(req.text)}-{uuid.uuid4().hex[:6]}"
    entry = {
        "id": plan_id,
        "created_at": ts,
        "request": req.text,
        "artifacts": artifacts,
    }
    idx = _load_index(repo_root)
    idx[plan_id] = entry
    _save_index(repo_root, idx)

    return {"message": "Planned and generated artifacts", "plan_id": plan_id, "artifacts": artifacts, "request": req.text}

@app.get("/plans")
def list_plans(limit: int = 20):
    repo_root = _repo_root()
    idx = _load_index(repo_root)
    vals = list(idx.values())
    vals.sort(key=lambda x: x.get("created_at",""), reverse=True)
    return {"plans": vals[:limit]}

@app.get("/plans/{plan_id}")
def get_plan(plan_id: str):
    repo_root = _repo_root()
    idx = _load_index(repo_root)
    if plan_id not in idx:
        raise HTTPException(status_code=404, detail="plan not found")
    return idx[plan_id]
