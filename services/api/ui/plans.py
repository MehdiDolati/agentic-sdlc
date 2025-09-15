from __future__ import annotations

from pathlib import Path as _P
from typing import Optional, Dict, Any

from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.api.core.shared import (
    _repo_root, _database_url, _create_engine, _render_markdown,
    _read_text_if_exists, _sort_key, _auth_enabled,
)
from services.api.core.repos import PlansRepoDB, ensure_plans_schema

router = APIRouter(tags=["ui"])

_TEMPLATES_DIR = _P(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.get("/", include_in_schema=False)
def ui_root():
    return RedirectResponse(url="/ui/plans")

@router.get("/ui", include_in_schema=False)
def ui_home():
    return RedirectResponse(url="/ui/plans")

@router.get("/ui/plans", response_class=HTMLResponse, include_in_schema=False)
def ui_plans(request: Request,
             q: Optional[str] = Query(None, alias="q"),
             sort: str = Query("created_at"),
             order: str = Query("desc"),
             limit: int = Query(20, ge=1, le=100),
             offset: int = Query(0, ge=0)):
    """
    Server-rendered plan list. Uses same backing index as /plans API.
    """
    repo_root = _repo_root()
    engine = _create_engine(_database_url(repo_root))
    plans = PlansRepoDB(engine).list()
    items = plans

    # mimic /plans search subset (simple contains on request + artifact paths)
    if q:
        ql = q.lower()
        def _matches(e: Dict[str, Any]) -> bool:
            if ql in (e.get("request") or "").lower():
                return True
            arts = e.get("artifacts") or {}
            for _, v in arts.items():
                if ql in str(v).lower():
                    return True
            return False
        items = [e for e in items if _matches(e)]

    # sort
    reverse = (order or "desc").lower() == "desc"
    items.sort(key=lambda e: _sort_key(e, sort or "created_at"), reverse=reverse)

    total = len(items)
    page_items = items[offset: offset + limit]

    ctx = {
        "request": request,
        "title": "Plans",
        "plans": page_items,
        "total": total,
        "page": (offset // limit) + 1,
        "limit": limit,
        "offset": offset,
        "q": q or "",
        "sort": sort or "created_at",
        "order": order or "desc",
    }

    # If HTMX paginates/searches we only re-render the table fragment
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(request,"plans_list_table.html", ctx)
    return templates.TemplateResponse(request,"plans_list.html", ctx)

@router.get("/ui/plans/{plan_id}", response_class=HTMLResponse, include_in_schema=False)
def ui_plan_detail(request: Request, plan_id: str):
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")    
    repo_root = _repo_root()
    engine = _create_engine(_database_url(repo_root))
    plan = PlansRepoDB(engine).get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    artifacts = plan.get("artifacts") or {}
    prd_rel = artifacts.get("prd")
    adr_rel = artifacts.get("adr")
    openapi_rel = artifacts.get("openapi")

    prd_html = _render_markdown(_read_text_if_exists(repo_root / prd_rel)) if prd_rel else None
    adr_html = _render_markdown(_read_text_if_exists(repo_root / adr_rel)) if adr_rel else None
    openapi_text = _read_text_if_exists(repo_root / openapi_rel) if openapi_rel else None

    ctx = {
        "request": request,
        "title": f"Plan {plan_id}",
        "plan": plan,
        "prd_rel": prd_rel, "prd_html": prd_html,
        "adr_rel": adr_rel, "adr_html": adr_html,
        "openapi_rel": openapi_rel, "openapi_text": openapi_text,
    }
    return templates.TemplateResponse(request,"plan_detail.html", ctx)


# HTMX partials for detail sections
@router.get("/ui/plans/{plan_id}/sections/prd", response_class=HTMLResponse, include_in_schema=False)
def ui_plan_section_prd(request: Request, plan_id: str):
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")    
    repo_root = _repo_root()
    engine = _create_engine(_database_url(repo_root))
    plan = PlansRepoDB(engine).get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    prd_rel = (plan.get("artifacts") or {}).get("prd")
    prd_html = _render_markdown(_read_text_if_exists(repo_root / prd_rel)) if prd_rel else None
    return templates.TemplateResponse(request,"section_prd.html", {
        "request": request, "prd_rel": prd_rel, "prd_html": prd_html
    })

@router.get("/ui/plans/{plan_id}/sections/adr", response_class=HTMLResponse, include_in_schema=False)
def ui_plan_section_adr(request: Request, plan_id: str):
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")    
    repo_root = _repo_root()
    engine = _create_engine(_database_url(repo_root))
    plan = PlansRepoDB(engine).get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    adr_rel = (plan.get("artifacts") or {}).get("adr")
    adr_html = _render_markdown(_read_text_if_exists(repo_root / adr_rel)) if adr_rel else None
    return templates.TemplateResponse(request,"section_adr.html", {
        "request": request, "adr_rel": adr_rel, "adr_html": adr_html
    })


@router.get("/ui/plans/{plan_id}/sections/openapi", response_class=HTMLResponse, include_in_schema=False)
def ui_plan_section_openapi(request: Request, plan_id: str):
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")    
    repo_root = _repo_root()
    engine = _create_engine(_database_url(repo_root))
    plan = PlansRepoDB(engine).get(plan_id)
    if not plan:
        # Render empty section (tests expect 200 + fragment, not 404)
        return templates.TemplateResponse(
            request,
            "section_openapi.html",
            {"request": request, "openapi_rel": None, "openapi_text": "(no OpenAPI yet)"},
        )

    openapi_rel = (plan.get("artifacts") or {}).get("openapi")
    openapi_text = _read_text_if_exists(repo_root / openapi_rel) if openapi_rel else None
    return templates.TemplateResponse(
        request,
        "section_openapi.html",
        {"request": request, "openapi_rel": openapi_rel, "openapi_text": openapi_text or "(no OpenAPI yet)"},
    )