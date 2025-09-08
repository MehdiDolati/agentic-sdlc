from __future__ import annotations
import base64, hmac, hashlib, json, time
from typing import Dict, Any, Optional

def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def _b64ud(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "==")

def _sign(secret: str, payload_b64: str) -> str:
    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    return _b64u(sig)

def create_token(secret: str, user_id: str, email: str, ttl_seconds: int = 3600) -> str:
    payload = {"uid": user_id, "email": email, "exp": int(time.time()) + ttl_seconds}
    payload_b64 = _b64u(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _sign(secret, payload_b64)
    return f"{payload_b64}.{sig}"

# -- token parsing -------------------------------------------------------------
def read_token(secret: str, token: str) -> Optional[Dict[str, Any]]:
    """
    Validates and returns the JWT-like payload we create in create_token().
    Our format is: <base64url(payload)>.<hex_signature>
    """
    try:
        payload_b64, sig = token.split(".", 1)
    except ValueError:
        return None

    # verify signature
    if not hmac.compare_digest(_sign(secret, payload_b64), sig):
        return None

    # decode payload
    try:
        raw = base64.urlsafe_b64decode(payload_b64 + "==")
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return None

    # expiry check
    if int(data.get("exp", 0)) < int(time.time()):
        return None

    return data

def verify_token(secret: str, token: str) -> Optional[Dict[str, Any]]:
    try:
        payload_b64, sig = token.split(".", 1)
        if not hmac.compare_digest(_sign(secret, payload_b64), sig):
            return None
        payload = json.loads(_b64ud(payload_b64))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

# --- compat wrapper (used by tests/old call sites) ---
def issue_bearer(secret: str, user_id: str, email: str) -> str:
    # Delegate to the real token builder
    return create_token(secret, user_id, email)
