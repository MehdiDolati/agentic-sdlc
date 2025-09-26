# services/api/app.py
from __future__ import annotations
from pathlib import Path
import sys
import re
import hmac, hashlib, base64
import services.api.core.shared as shared
from contextlib import asynccontextmanager
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
import logging
 
logger = logging.getLogger(__name__)
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
from services.api.core.repos import PlansRepoDB, NotesRepoDB, ensure_plans_schema, ensure_runs_schema, ensure_notes_schema, ensure_projects_schema
from services.api.ui.plans import router as ui_plans_router
from services.api.ui.auth import router as ui_auth_router
from services.api.auth.tokens import read_token
from services.api.auth.routes import router as auth_router, get_current_user
from services.api.runs.routes import router as runs_router
from services.api.routes.ui_requests import router as ui_requests_router
from services.api.ui.plans import router as ui_plans_router
from services.api.ui.settings import router as ui_settings_router

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
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, FileResponse
from services.api.db import psycopg_conninfo_from_env, dsn_summary

import psycopg

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

app = FastAPI(title="Agentic SDLC API", version="0.1.0", docs_url="/docs", openapi_url="/openapi.json")
app.include_router(ui_requests_router)
app.include_router(ui_plans_router)
app.include_router(ui_auth_router)
app.include_router(auth_router)
app.include_router(runs_router)
app.include_router(ui_settings_router)

# --- UI wiring (templates + static) ---
AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-secret")
_THIS_DIR = Path(__file__).resolve().parent
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
        data = read_token(AUTH_SECRET, tok)
    except Exception:
        return None
    if not data:
        return None
    return data.get("uid")

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

def _engine():
    # Always resolve against the current repo root (now respects APP_STATE_DIR)
    return _create_engine(_database_url(shared._repo_root()))

def _init_schemas():
    eng = _engine()
    try:
        ensure_projects_schema(eng)
    except Exception:
        pass
    try:
        ensure_plans_schema(eng)
    except Exception:
        pass
    try:
        ensure_runs_schema(eng)
    except Exception:
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup (was @app.on_event("startup")) ----
    _init_schemas()
    yield
    # ---- shutdown (was @app.on_event("shutdown")) ----
    # nothing to do here right now
    # e.g., close DBs/threads if you add them later
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
def api_notes_create(payload: Dict[str, Any], request: Request):
    u = _user_from_http(request)
    if _auth_enabled() and u.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")    
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
def api_create_item(payload: Dict[str, Any], request: Request):
    u = _user_from_http(request)
    if _auth_enabled() and u.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")    
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
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")    
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

# Minimal root page — snapshot tests look for 'hello endpoint'
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request):
    return HTMLResponse("<h1>hello endpoint</h1>")
    
# -------------------- Flash-friendly exception handlers --------------------
def _wants_html_fragment(req: Request) -> bool:
    # When requests come from HTMX, prefer an HTML flash fragment.
    return req.headers.get("HX-Request", "").lower() == "true"

@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    if request.headers.get("HX-Request") == "true":
        ctx = {
            "request": request,
            "level": "error",
            "title": str(exc.status_code),
            "message": exc.detail or "Request failed.",
        }
        return templates.TemplateResponse("_flash.html", ctx, status_code=exc.status_code)
    return JSONResponse({"detail": exc.detail or "Request failed."}, status_code=exc.status_code)

# HTMX-aware 5xx catch-all
@app.exception_handler(Exception)
async def unhandled_exc_handler(request: Request, exc: Exception):
    if request.headers.get("HX-Request") == "true":
        ctx = {
            "request": request,
            "level": "error",
            "title": "500",
            "message": "Unexpected error.",
        }
        return templates.TemplateResponse("_flash.html", ctx, status_code=HTTP_500_INTERNAL_SERVER_ERROR)
    return JSONResponse({"detail": "Unexpected error."}, status_code=HTTP_500_INTERNAL_SERVER_ERROR)

@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    if _wants_html_fragment(request):
        return templates.TemplateResponse(
            "_error_fragment.html",
            {
                "request": request,
                "flash": {"level": "error", "title": "Validation error", "message": "Validation error"},
                "target_id": _hx_target_id(request),   # <-- add this
            },
            status_code=422,
        )
    return JSONResponse({"detail": exc.errors()}, status_code=422)

FAVICON_PATH = Path(__file__).parent / "static" / "favicon.ico"
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    if FAVICON_PATH.exists():
        return FileResponse(FAVICON_PATH)
    # Optional: avoid 404 noise if it’s missing
    return FileResponse(FAVICON_PATH, status_code=200)  # or return a 204       
    
def _hx_target_id(request: Request) -> str | None:
    # HTMX sends the id of the target element (if it has an id)
    return request.headers.get("HX-Target")
    