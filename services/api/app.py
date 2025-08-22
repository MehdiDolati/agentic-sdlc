from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import json, uuid, importlib, sys

# --- make both import styles work (pytest & uvicorn reload) ---
ROOT = Path(__file__).resolve().parents[2]   # repo root
API_DIR = Path(__file__).resolve().parents[1]  # services/api
for p in (str(ROOT), str(API_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

def _import_one(*mods):
    seen = set()
    for m in mods:
        if not m or m in seen:
            continue
        seen.add(m)
        try:
            return importlib.import_module(m)
        except ImportError:
            pass
    raise ImportError(f"Could not import any of: {mods}")

_pkg = __package__  # 'services.api' when run as a package; None under pytest

# planner
planner_mod = _import_one(
    f"{_pkg}.planner" if _pkg else None,
    "services.api.planner",
    "planner",
)
plan_request = getattr(planner_mod, "plan_request")

# routers
create_mod = _import_one(
    f"{_pkg}.routes.create" if _pkg else None,
    "services.api.routes.create",
    "routes.create",
)
notes_mod = _import_one(
    f"{_pkg}.routes.notes" if _pkg else None,
    "services.api.routes.notes",
    "routes.notes",
)
create_router = getattr(create_mod, "router")
notes_router  = getattr(notes_mod, "router")

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
