# services/api/db.py
from __future__ import annotations

import os
import re
import time
from typing import Optional, Tuple
# psycopg is only needed when we actually connect to Postgres.
# Make it optional so SQLite test runs don't fail at import time.
try:
    import psycopg  # type: ignore
except Exception:  # ImportError on CI if not installed
    psycopg = None  # type: ignore

REDACTED = "****"

def dsn_summary(url: str) -> str:
    """
    Return a redacted version of a DB URL for logs (mask only the password).
    Examples:
      postgresql://user:pass@host:5432/db -> postgresql://user:****@host:5432/db
    """
    if not url:
        return ""
    return re.sub(r"(://[^:]+):[^@]*@", r"\1:" + REDACTED + "@", url)

def _normalize_db_url(url: str) -> str:
    """
    Normalize common variants to a psycopg-compatible URI:
    - postgresql+psycopg://  -> postgresql://
    - postgres://            -> postgresql://
    """
    u = (url or "").strip()
    if not u:
        return u
    if u.startswith("postgresql+psycopg://"):
        u = "postgresql://" + u[len("postgresql+psycopg://"):]
    elif u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://"):]
    return u

def psycopg_conninfo_from_env() -> Optional[str]:
    """
    Produce a libpq-compatible DSN for psycopg from DATABASE_URL (if set).
    Accepts SQLAlchemy-style 'postgresql+psycopg://' and normalizes it.
    """
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        return None
    return _normalize_db_url(raw)

def wait_for_db(max_attempts: int = 30, sleep_sec: float = 1.0, log=print) -> bool:
    """
    Poll the database until it's reachable (SELECT 1) or attempts exhausted.
    Uses DATABASE_URL from the environment and psycopg.
    """
    dsn = psycopg_conninfo_from_env()
    if not dsn:
        log("[db_init] DATABASE_URL is empty; cannot wait for DB")
        return False

    log(f"[db_init] normalized DSN (redacted): {dsn_summary(dsn)}")
    for i in range(1, max_attempts + 1):
        try:
            if psycopg is None:
                raise RuntimeError("psycopg not installed; Postgres not available in this environment")
            with psycopg.connect(dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            log("[db_init] DB ready")
            return True
        except Exception as e:
            log(f"[db_init] waiting for db ({i}/{max_attempts})... {e}")
            time.sleep(sleep_sec)

    log("[db_init] ERROR: DB not ready after retries")
    return False