from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from services.api.auth.routes import get_current_user
from services.api.core.shared import _auth_enabled

import services.api.core.shared as shared
from services.api.planner.core import plan_request  # deterministic planner fallback
from services.api.planner.openapi_gen import generate_openapi  # blueprint→OpenAPI

# Create a local templates instance to avoid importing app.py (prevents circular import).
_THIS_FILE = Path(__file__).resolve()
_TEMPLATES_DIR = _THIS_FILE.parents[2] / "templates"  # <repo>/services/templates
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()

# Render the form
@router.get("/ui/requests/new", response_class=HTMLResponse)
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
ui_requests_router = APIRouter()

# Handle submission: build a draft plan + artifacts for review
@router.post("/ui/requests", response_class=HTMLResponse)
def submit_request(
    request: Request,
    project_vision: str = Form(...),
    agent_mode: str = Form("single"),
    llm_provider: str = Form("none"),
    plan_id: Optional[str] = Form(None),
    user: Dict[str, Any] = Depends(get_current_user),
):
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")
    repo_root = shared._repo_root()
    draft = plan_request(project_vision, repo_root, owner="ui")  # writes docs/* deterministically
    # If user provided a Plan ID, persist later via POST /plans; for now, preview.

    # Ensure we have an OpenAPI draft in memory even if generator module not present
    try:
        blueprint = {
            "info": {"title": "Agentic Feature API", "version": "0.1.0",
                     "description": project_vision[:400]},
            "paths": [
                {"path": "/plans", "method": "get", "summary": "List Plans",
                 "responses": {"200": {"description": "OK"}}},
            ],
            "security_schemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
            "default_security": ["bearerAuth"],
        }
        openapi = generate_openapi(blueprint)  # raises if invalid
    except Exception:
        # Conservative fallback: show the skeleton used in planner.core
        openapi = {"openapi": "3.1.0", "info": {"title": "Agentic Feature API", "version": "0.1.0"}, "paths": {}}

    return templates.TemplateResponse(
        request,
        "requests_review.html",
        {
            "plan": draft,
            "openapi_json": openapi,
            "project_vision": project_vision,
            "agent_mode": agent_mode,
            "llm_provider": llm_provider,
            "suggested_plan_id": plan_id or draft.get("id") or "",
        },
    )
