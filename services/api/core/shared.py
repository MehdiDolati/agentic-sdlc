from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL
import markdown as _markdown
import secrets

@lru_cache(maxsize=1)
def _repo_root() -> Path:
    # Prefer env override (used in docker/CI)
    env_root = os.getenv("REPO_ROOT")
    if env_root:
        p = Path(env_root)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Default to repository root (current /app in image). If not writable, use /tmp.
    p = Path.cwd()
    try:
        (p / ".write_test").write_text("ok", encoding="utf-8")
        (p / ".write_test").unlink(missing_ok=True)
        return p
    except Exception:
        tmp = Path("/tmp/agentic-sdlc")
        tmp.mkdir(parents=True, exist_ok=True)
        return tmp

def _reset_repo_root_cache_for_tests() -> None:
    _repo_root.cache_clear()


def _plans_db_path(repo_root: Path | str | None = None) -> Path:
    base = Path(repo_root) if repo_root is not None else _repo_root()
    db_path = base / "docs" / "plans" / "plans.db"
    # Ensure directories exist for SQLite (prevents OperationalError)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path

def _database_url(repo_root: Path | str | None) -> str:
    """
    If DATABASE_URL is set, return it verbatim.
    Otherwise, return a portable SQLite URL pointing to docs/plans/plans.db
    under the given repo_root (or the cached _repo_root() if None).
    """
    url = (os.getenv("DATABASE_URL") or "").strip()
    if url:
        return url

    db_path = _plans_db_path(repo_root)
    # Use URL.create to avoid Windows backslash issues and to set options cleanly
    url_obj = URL.create(
        "sqlite",
        database=db_path.as_posix(),       # forward slashes; fine on Windows
        query={"check_same_thread": "false"},
    )
    # Return a string because callers already expect str
    return url_obj.render_as_string(hide_password=False)


def _create_engine(url: str) -> Engine:
    # Keep the same options you had (future=True) for SQLAlchemy 2.x behavior.
    return create_engine(url, future=True)


def _render_markdown(md: Optional[str]) -> Optional[str]:
    if not md:
        return None
    return _markdown.markdown(md, extensions=["fenced_code", "tables", "toc"])

def _read_text_if_exists(p: Path) -> Optional[str]:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return None

def _sort_key(entry: Dict[str, Any], key: Any) -> Any:
    # Coerce FastAPI Query(...) default or tuple/list to a plain string
    k = key
    if isinstance(k, (list, tuple)):
        k = k[0] if k else "created_at"
    # FastAPI's Query object has a `.default` with the actual default value
    if hasattr(k, "default"):
        default_val = getattr(k, "default")
        if isinstance(default_val, str):
            k = default_val
    if not isinstance(k, str):
        k = "created_at"

    k = k.strip().lower()

    if k in {"created_at", "created"}:
        return entry.get("created_at", "")
    if k in {"request", "goal"}:
        return entry.get("request", "")
    if k == "id":
        return entry.get("id", "")

    # fall back to top-level field if present
    return entry.get(k, "")

def _auth_enabled() -> bool:
    """Auth is OFF by default for backward compatibility.
       Enable by setting AUTH_MODE to one of: on, true, enabled, 1
    """
    return (os.getenv("AUTH_MODE") or "").strip().lower() in {"on", "true", "enabled", "1"}

def _new_id(prefix: str) -> str:
    """Generate IDs. Tests require user IDs to start with 'u_'."""
    if prefix == "user":
        # e.g. u_3f8a2a4b9c1d  (hex, deterministic-enough and short)
        return f"u_{secrets.token_hex(6)}"
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    if prefix in {"u", "user"}:
        # tests expect user IDs to start with "u_"
        return f"u_{secrets.token_hex(3)}"
    return f"{ts}-{prefix}-{secrets.token_hex(3)}"

def _app_state_dir() -> Path:
    """
    Where the app can write state (users.json, etc).
    Priority:
      1) APP_STATE_DIR env
      2) repo root (current file two levels up)  -> <repo>/   (local dev/tests)
    """
    env_dir = os.getenv("APP_STATE_DIR")
    if env_dir:
        p = Path(env_dir)
    else:
        # repo root = services/api/../../
        p = Path(__file__).resolve().parents[2]
    return p

def _users_file() -> Path:
    """
    Users JSON location.
    Priority:
      1) AUTH_USERS_FILE env (absolute path)
      2) <APP_STATE_DIR>/.data/users.json
    Ensures parent dir exists.
    """
    override = os.getenv("AUTH_USERS_FILE")
    if override:
        uf = Path(override)
    else:
        uf = _app_state_dir() / ".data" / "users.json"
    uf.parent.mkdir(parents=True, exist_ok=True)
    return uf
