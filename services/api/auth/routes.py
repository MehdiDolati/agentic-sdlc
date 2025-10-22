from __future__ import annotations

import json
import hmac, hashlib, base64
import secrets
from typing import Any, Dict, Optional
from fastapi import APIRouter, Body, Cookie, Header, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from services.api.auth.users import FileUserStore
from services.api.core.shared import _new_id
from services.api.core.shared import _users_file
from services.api.auth.tokens import AUTH_SECRET, issue_bearer, read_token
from services.api.auth.passwords import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
_user_store = FileUserStore(_users_file())

def _hash_pw(pw: str) -> str:
    return hashlib.sha256((pw or "").encode("utf-8")).hexdigest()

def _get_user_by_id(uid: str) -> Optional[Dict[str, Any]]:
    """Get user by ID from users file."""
    uf = _users_file()
    try:
        users_raw = json.loads(uf.read_text(encoding="utf-8"))
    except Exception:
        users_raw = {}

    def _iter_user_dicts(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                if isinstance(v, dict):
                    yield v
        elif isinstance(obj, list):
            for v in obj:
                if isinstance(v, dict):
                    yield v

    return next((u for u in _iter_user_dicts(users_raw) if u.get("id") == uid), None)

def get_current_user(
    request: Request,
    authorization: str = Header(default=""),
    session: Optional[str] = Cookie(default=None),
) -> Dict[str, Any]:
    """
    Returns {id, email, role}. If a valid Bearer token (or session cookie) is present,
    hydrate from the token; otherwise fall back to the public user.
    """
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(None, 1)[1].strip()
    elif session:
        token = session

    if token:
        data = read_token(AUTH_SECRET, token)
        if data and data.get("uid"):
            user_data = _get_user_by_id(data["uid"])
            if user_data:
                return {
                    "id": user_data["id"],
                    "email": (user_data.get("email") or "").strip().lower(),
                    "role": user_data.get("role", "user")
                }

    # default public user
    return {"id": "public", "email": "public@example.com", "role": "public"}

@router.post("/register")
def register(payload: Dict[str, str] = Body(...)):
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password required")

    # Read users.json directly
    uf = _users_file()
    try:
        users_raw = json.loads(uf.read_text(encoding="utf-8"))
    except Exception:
        users_raw = {}

    def _iter_user_dicts(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                if isinstance(v, dict):
                    yield v
        elif isinstance(obj, list):
            for v in obj:
                if isinstance(v, dict):
                    yield v

    # check duplicate by email safely
    for u in _iter_user_dicts(users_raw):
        if str(u.get("email", "")).strip().lower() == email:
            # behave idempotently
            return {"status": "ok", "user": {"id": u.get("id"), "email": email, "role": u.get("role", "user")}}

    # persist new user with default role
    uid = _new_id("u")
    record = {
        "id": uid, 
        "email": email, 
        "password_hash": _hash_pw(password),
        "role": "user"  # default role
    }

    if isinstance(users_raw, dict):
        users_raw[uid] = record
    elif isinstance(users_raw, list):
        users_raw.append(record)
    else:
        users_raw = {uid: record}

    uf.parent.mkdir(parents=True, exist_ok=True)
    uf.write_text(json.dumps(users_raw, indent=2), encoding="utf-8")
    
    return {"status": "ok", "user": {"id": uid, "email": email, "role": "user"}}

@router.post("/login")
def auth_login(payload: Dict[str, str] = Body(...)):
    email = (payload.get("email") or payload.get("username") or "").strip().lower()
    password = payload.get("password") or ""
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password required")

    # Read users.json directly
    uf = _users_file()
    try:
        users_raw = json.loads(uf.read_text(encoding="utf-8"))
        print(f"[DEBUG] Loaded users_raw type: {type(users_raw)}, keys: {list(users_raw.keys()) if isinstance(users_raw, dict) else 'N/A'}")
    except Exception as e:
        print(f"[DEBUG] Failed to load users.json: {e}")
        users_raw = {}

    def _iter_user_records(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                if isinstance(v, dict):
                    yield v
        elif isinstance(obj, list):
            for v in obj:
                if isinstance(v, dict):
                    yield v

    user = next(
        (u for u in _iter_user_records(users_raw)
         if str(u.get("email", "")).strip().lower() == email),
        None
    )
    print(f"[DEBUG] Found user: {user is not None}")
    if user:
        print(f"[DEBUG] User email: {user.get('email')}, has password_hash: {bool(user.get('password_hash'))}")
    if not user:
        raise HTTPException(status_code=400, detail="invalid credentials")

    # Verify password
    stored = user.get("password_hash") or user.get("password") or ""
    if not verify_password(password, stored):
        print(f"[DEBUG] verify_password returned False")
        raise HTTPException(status_code=400, detail="invalid credentials")

    # Normalize user id for tokens
    uid = str(user.get("id") or "").strip()
    if not uid.startswith("u_"):
        try:
            tail = uid.split("-")[-1]
            uid = f"u_{tail[:6]}" if tail else f"u_{secrets.token_hex(3)}"
        except Exception:
            uid = f"u_{secrets.token_hex(3)}"
    
    token = issue_bearer(AUTH_SECRET, uid, user["email"])
    resp = JSONResponse({
        "ok": True,
        "access_token": token,
        "token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"], 
            "email": user["email"],
            "role": user.get("role", "user")
        },
    })
    # Set session cookie
    resp.set_cookie("session", token, httponly=False, samesite="lax", max_age=86400)  # 24 hours
    return resp

@router.post("/logout")
def auth_logout():
    """Logout user by clearing session cookie."""
    resp = JSONResponse({"ok": True, "message": "Logged out successfully"})
    resp.delete_cookie("session")
    return resp

@router.get("/me")
def auth_me(user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user info including role."""
    return user

@router.post("/admin/promote")
def promote_to_admin(
    target_email: str = Body(..., embed=True),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Promote a user to admin role (requires admin privileges)."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    uf = _users_file()
    try:
        users_raw = json.loads(uf.read_text(encoding="utf-8"))
    except Exception:
        users_raw = {}

    # Find target user
    target_user = None
    user_key = None
    
    if isinstance(users_raw, dict):
        for uid, u_data in users_raw.items():
            if isinstance(u_data, dict) and u_data.get("email") == target_email:
                target_user = u_data
                user_key = uid
                break
    elif isinstance(users_raw, list):
        for i, u_data in enumerate(users_raw):
            if isinstance(u_data, dict) and u_data.get("email") == target_email:
                target_user = u_data
                user_key = i
                break

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update role
    target_user["role"] = "admin"
    
    # Save back to file
    if isinstance(users_raw, dict):
        users_raw[user_key] = target_user
    elif isinstance(users_raw, list):
        users_raw[user_key] = target_user
    
    uf.write_text(json.dumps(users_raw, indent=2), encoding="utf-8")
    
    return {"status": "ok", "message": f"User {target_email} promoted to admin"}