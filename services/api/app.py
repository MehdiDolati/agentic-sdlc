# services/api/app.py
from __future__ import annotations
from pathlib import Path
import sys
import re
import hmac, hashlib, base64
import services.api.core.shared as shared

from services.api.core.shared import (
    _database_url,
    _create_engine,
    _render_markdown,
    _read_text_if_exists,
    _plans_index_path,
    _save_index,
    _load_index,
    _append_run_to_index,
    _sort_key,
    _auth_enabled,
    _new_id,
    AUTH_MODE
)
from services.api.core.repos import PlansRepoDB, NotesRepoDB, ensure_plans_schema, ensure_runs_schema, ensure_notes_schema
from services.api.ui.plans import router as ui_plans_router
from services.api.ui.auth import router as ui_auth_router
from services.api.auth.tokens import read_token
from services.api.auth.routes import router as auth_router, get_current_user
from services.api.runs.routes import router as runs_router


_BASE_DIR = Path(__file__).resolve().parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

# Module-level override the tests can point at
_STORE_ROOT: Optional[Path] = None

import os, uuid, json, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field, EmailStr
from fastapi import Query
from fastapi import Header, Body, BackgroundTasks, FastAPI, HTTPException, status, Depends, Cookie, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from services.api.db import psycopg_conninfo_from_env, dsn_summary

import psycopg

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Agentic SDLC API", version="0.1.0")
app.include_router(ui_plans_router)
app.include_router(ui_auth_router)
app.include_router(auth_router)
app.include_router(runs_router)

# --- UI wiring (templates + static) ---
AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-secret")
_THIS_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
_STATIC_DIR = _THIS_DIR / "static"

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# -------------------- Artifact view endpoints --------------------
    
def _write_text_abs(abs_path: Path, content: str) -> None:
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")

# --------------------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------------------


def _store_root() -> Path:
    """Return the active store root (tests may retarget this)."""
    return _STORE_ROOT if _STORE_ROOT is not None else shared._repo_root()

def _retarget_store(p: Path) -> None:
    """Used by tests to point the store at a temp dir."""
    global _STORE_ROOT
    _STORE_ROOT = Path(p)

def _extract_bearer(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def _authed_user_id(request: Request) -> str | None:
    tok = _extract_bearer_from_request(request)
    if not tok:
        return None
    try:
        return parse_token(AUTH_SECRET, tok).get("uid")
    except Exception:
        return None

# ---------- Plans search/filter helpers ----------

def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("ascii"))

def _sign(secret: str, msg: str) -> str:
    return _b64u(hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest())

def _extract_bearer_from_request(req: Request) -> str | None:
    auth = req.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    # tests also accept cookie-based session
    if "session" in req.cookies:
        return req.cookies["session"]
    return None

_ARTIFACT_EXT_MAP = {
    "prd": {".md", ".markdown"},
    "openapi": {".yaml", ".yml", ".json"},
    "doc": {".md", ".markdown", ".rst"},
    "code": {".py", ".ts", ".js", ".go", ".java", ".cs", ".rb"},
}

def _to_dt(ts: str) -> Optional[datetime]:
    # ts in our index is "%Y%m%d%H%M%S" (UTC) from create_request()
    try:
        return datetime.strptime(ts, "%Y%m%d%H%M%S")
    except Exception:
        return None

def _ci_or_pytest() -> bool:
    return bool(os.getenv("CI") or os.getenv("PYTEST_CURRENT_TEST"))

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _user_from_http(request: Request) -> Dict[str, Any]:
    """Resolve the current user from raw HTTP headers/cookies (no DI)."""
    token = None
    auth = (request.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        token = auth.split(None, 1)[1].strip()
    if not token:
        token = request.cookies.get("session")

    if token:
        data = read_token(AUTH_SECRET, token)
        if data and data.get("uid"):
            return {
                "id": data["uid"],
                "email": (data.get("email") or "").strip().lower(),
            }
    return {"id": "public", "email": "public@example.com"}

# Initialize the repo once at import time
_DB_ENGINE = _create_engine(_database_url(shared._repo_root()))
_NOTES_REPO = NotesRepoDB(_DB_ENGINE)
# ----------------------------------------------------------------

# ---------- Plans DB (defined earlier in your file if not yet) ----------
# (keep as you already added for Issue #33)
# _PLANS_METADATA, _PLANS_TABLE, PlansRepoDB, ensure_plans_schema(...)
# Ensure schema on import:
try:
    ensure_plans_schema(_DB_ENGINE)
except Exception:
    pass


ensure_runs_schema(_DB_ENGINE)

# --------------------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------------------
@app.get("/health")
def health():
    if os.getenv("STARTUP_DEBUG"):
        try:
            dsn = psycopg_conninfo_from_env()
            print(f"[app] normalized DSN: {dsn_summary(str(dsn))}")
        except Exception as e:
            print(f"[app] DSN normalization failed: {e!r}")
    return {"status": "ok"}


# In-memory notes store (simple; tests only verify CRUD works)
_NOTES: Dict[str, Dict[str, Any]] = {}

# --------------------------------------------------------------------------------------
# API stubs used by tests
# --------------------------------------------------------------------------------------
@app.get("/api/notes")
def api_notes_list():
    return list(_NOTES.values())

@app.post("/api/notes", status_code=201)
def api_notes_create(payload: Dict[str, Any]):
    nid = uuid.uuid4().hex[:8]
    doc = {"id": nid, **payload}
    _NOTES[nid] = doc
    return doc

@app.get("/api/notes/{note_id}")
def api_notes_get(note_id: str):
    doc = _NOTES.get(note_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Note not found")
    return doc

@app.put("/api/notes/{note_id}")
def api_notes_put(note_id: str, payload: Dict[str, Any]):
    if note_id not in _NOTES:
        raise HTTPException(status_code=404, detail="Note not found")
    _NOTES[note_id] = {"id": note_id, **payload}
    return _NOTES[note_id]

@app.delete("/api/notes/{note_id}", status_code=204)
def api_notes_delete(note_id: str):
    _NOTES.pop(note_id, None)
    return JSONResponse(status_code=204, content=None)
    
# --------------------------------------------------------------------------------------
# Simple "create" CRUD (used by tests in test_create_routes.py)
# --------------------------------------------------------------------------------------
_CREATE_STORE: Dict[str, Dict[str, Any]] = {}

@app.get("/api/create")
def api_create_list():
    # initially empty; grows as POSTs happen
    return list(_CREATE_STORE.values())

@app.post("/api/create", status_code=201)
def api_create_item(payload: Dict[str, Any]):
    iid = uuid.uuid4().hex[:8]
    doc = {"id": iid, **payload}
    _CREATE_STORE[iid] = doc
    return doc

@app.get("/api/create/{item_id}")
def api_create_get(item_id: str):
    doc = _CREATE_STORE.get(item_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")
    return doc

@app.put("/api/create/{item_id}")
def api_create_put(item_id: str, payload: Dict[str, Any]):
    if item_id not in _CREATE_STORE:
        raise HTTPException(status_code=404, detail="Item not found")
    _CREATE_STORE[item_id] = {"id": item_id, **payload}
    return _CREATE_STORE[item_id]

@app.delete("/api/create/{item_id}", status_code=204)
def api_create_delete(item_id: str):
    _CREATE_STORE.pop(item_id, None)
    return JSONResponse(status_code=204, content=None)
    
# add this route (dev-use)
@app.post("/orchestrator/run")
def orchestrator_run(payload: Dict[str, Any]):
    steps = payload.get("steps", [])
    dry_run = bool(payload.get("dry_run", False))
    results = run_steps(steps, cwd=shared._repo_root(), dry_run=dry_run)
    # serialize dataclasses
    return [r.__dict__ for r in results]

@app.middleware("http")
async def _attach_user_to_request(request: Request, call_next):
    # Expose current user to templates, derived from raw HTTP headers/cookies
    request.state.user = _user_from_http(request)
    return await call_next(request)