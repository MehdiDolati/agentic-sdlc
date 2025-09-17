# services/api/routes/ui_requests.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

import services.api.core.shared as shared
from services.api.auth.routes import get_current_user
from services.api.core.shared import _auth_enabled
from services.api.planner.core import plan_request

# Optional generator; tests will monkeypatch this symbol on THIS module
try:
    from services.api.planner.openapi_gen import generate_openapi
except Exception:
    def generate_openapi(_bp: dict) -> dict:
        raise RuntimeError("openapi generator unavailable")

# Local templates (avoid importing app.py to prevent circulars)
_THIS_FILE = Path(__file__).resolve()
_TEMPLATES_DIR = _THIS_FILE.parents[2] / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(tags=["ui"], include_in_schema=False)

# ---- GET form pages (both legacy and current paths) ----
@router.get("/ui/requests", response_class=HTMLResponse)
@router.get("/requests/new", response_class=HTMLResponse)
def new_request_form(request: Request):
    return templates.TemplateResponse(
        request,
        "requests_new.html",
        {
            "providers": ["none", "openai", "anthropic", "azure", "local"],
            "modes": ["single", "multi"],
            "default_provider": "none",
            "default_mode": "single",
        },
    )

# ---- Unified submit; mounted on BOTH /requests and /ui/requests ----
async def _handle_submit(request: Request, user: Dict[str, Any]) -> HTMLResponse | JSONResponse:
    # Single auth gate for both modes
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    repo_root = shared._repo_root()
    ctype = (request.headers.get("content-type") or "").lower()

    # JSON API path
    if "application/json" in ctype:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid JSON body")
        vision = (body.get("text") or body.get("goal") or "").strip()
        if not vision:
            raise HTTPException(status_code=422, detail="Field 'text' (or legacy 'goal') required")
        draft = plan_request(vision, repo_root, owner="ui")
        return JSONResponse(
            {"plan_id": draft.get("id"), "artifacts": draft.get("artifacts", {}), "request": draft.get("request")}
        )

    # HTML form path
    form = await request.form()
    vision = (str(form.get("project_vision") or form.get("goal") or "")).strip()
    if not vision:
        raise HTTPException(status_code=422, detail="project_vision/goal required")

    agent_mode = (str(form.get("agent_mode") or "single")).strip()
    llm_provider = (str(form.get("llm_provider") or "none")).strip()
    plan_id = (str(form.get("plan_id") or "")).strip()

    draft = plan_request(vision, repo_root, owner="ui")

    try:
        blueprint = {
            "info": {"title": "Agentic Feature API", "version": "0.1.0", "description": vision[:400]},
            "paths": [{"path": "/plans", "method": "get", "summary": "List Plans", "responses": {"200": {"description": "OK"}}}],
            "security_schemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
            "default_security": ["bearerAuth"],
        }
        openapi_json = generate_openapi(blueprint)
    except Exception:
        openapi_json = {"openapi": "3.1.0", "info": {"title": "Agentic Feature API", "version": "0.1.0"}, "paths": {}}

    # Avoid importing app.py; render via our local templates
    return templates.TemplateResponse(
        request,
        "requests_review.html",
        {
            "plan": draft,
            "openapi_json": openapi_json,
            "project_vision": vision,
            "agent_mode": agent_mode,
            "llm_provider": llm_provider,
            "suggested_plan_id": plan_id or draft.get("id") or "",
        },
    )

@router.post("/requests")
async def submit_request(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    return await _handle_submit(request, user)

@router.post("/ui/requests")
async def submit_request_legacy(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    return await _handle_submit(request, user)
