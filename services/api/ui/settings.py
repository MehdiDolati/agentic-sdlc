from __future__ import annotations
from typing import Dict, Any

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path

from fastapi.templating import Jinja2Templates
_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
from services.api.core import shared
from services.api.core.settings import load_settings, update_settings

router = APIRouter(tags=["ui"], include_in_schema=False)

@router.get("/ui/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    state_dir: Path = shared._repo_root()
    cfg = load_settings(state_dir)
    ctx = {
        "request": request,
        "title": "Settings",
        "cfg": cfg,
        "providers": ["none", "openai", "anthropic", "azure", "local"],
        "modes": ["single", "multi"],
    }
    ctx["flash"] = {"level": "success", "title": "Saved", "message": "Tasks updated."}
    return templates.TemplateResponse(request, "settings.html", ctx)

@router.post("/ui/settings", response_class=HTMLResponse)
def settings_save(
    request: Request,
    planner_mode: str = Form("single"),
    default_provider: str = Form("none"),
    api_base_url: str = Form(""),
    auth_enabled: bool = Form(False),
    multi_agent_enabled: bool = Form(False),
):
    state_dir: Path = shared._repo_root()
    # Normalize values
    planner_mode = planner_mode if planner_mode in ("single", "multi") else "single"
    default_provider = default_provider if default_provider in ("none", "openai", "anthropic", "azure", "local") else "none"
    api_base_url = (api_base_url or "").strip()
    # Persist
    cfg = update_settings(
        state_dir,
        {
            "planner_mode": planner_mode,
            "default_provider": default_provider,
            "api_base_url": api_base_url,
            "auth_enabled": bool(auth_enabled),
            "multi_agent_enabled": bool(multi_agent_enabled),
        },
    )
    ctx = {
        "request": request,
        "title": "Settings",
        "cfg": cfg,
        "providers": ["none", "openai", "anthropic", "azure", "local"],
        "modes": ["single", "multi"],
        "saved": True,
    }
    # Return full page so direct POST in tests works; HTMX can also target a fragment.
    ctx["flash"] = {"level": "success", "title": "Saved", "message": "Tasks updated."}
    return templates.TemplateResponse(request, "settings.html", ctx)
