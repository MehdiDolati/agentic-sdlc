from __future__ import annotations

import os, json
from fastapi import APIRouter, Request, Depends, Header, Cookie, Body
from typing import Optional
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
from pathlib import Path
from services.api.auth.passwords import hash_password, verify_password
from services.api.auth.tokens import create_token, issue_bearer, read_token, verify_token as verify_bearer
from fastapi.templating import Jinja2Templates

_THIS_FILE = Path(__file__).resolve()
_TEMPLATES_DIR = _THIS_FILE.parents[2] / "templates"  # <repo>/services/templates
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
router = APIRouter(tags=["ui"])

@router.get("/ui/logout", include_in_schema=False)
def ui_logout() -> RedirectResponse:
    resp = RedirectResponse(url="/ui/login")
    resp.delete_cookie("session")
    return resp


@router.get("/ui/login", response_class=HTMLResponse, include_in_schema=False)
def ui_login(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "title": "Login"}
    )

@router.get("/ui/register", response_class=HTMLResponse, include_in_schema=False)
def ui_register(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html",
        {"request": request, "title": "Register"}
    )

@router.post("/ui/logout", include_in_schema=False)
def ui_logout_post():
    resp = RedirectResponse(url="/ui/login", status_code=303)
    resp.delete_cookie("session")
    return resp