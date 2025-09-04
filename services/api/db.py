import os, time
from fastapi import APIRouter, HTTPException
from typing import Optional
import psycopg
try:
    import psycopg2
except Exception as e:
    psycopg2 = None

REDACTED = "****"

router = APIRouter(prefix="/db", tags=["db"])

@router.get("/health")
def db_health():
    url_env = os.getenv("DB_URL")
    if not (os.getenv("POSTGRES_CONNINFO") or os.getenv("DATABASE_URL") or url_env):
        return {"status": "disabled"}
    if psycopg2 is None:
        raise HTTPException(status_code=500, detail="psycopg2 not installed")
    try:
        conn = psycopg2.connect(psycopg_conninfo_from_env())
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            row = cur.fetchone()
        conn.close()
        return {"status": "ok", "result": row[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

def _redact_password(uri: str) -> str:
    # redact only the password section of a URI (…://user:PASSWORD@host/…)
    return re.sub(r'(://[^:]+):[^@]*@', r'\1:****@', uri)

def dsn_summary(url: str) -> str:
    """Redact password for logs."""
    if not url:
        return ""
    # redact :password@ in URI
    return url.replace(
        url.split("@")[0],
        url.split(":")[0] + f":{REDACTED}@" if "@" in url else url.split(":")[0] + f":{REDACTED}"
    )

def _normalize_db_url(url: str) -> str:
    """
    Normalize common variants to a psycopg-compatible URI:
    - postgresql+psycopg://  -> postgresql://
    - postgres://            -> postgresql://
    """
    u = url.strip()
    if not u:
        return u
    if u.startswith("postgresql+psycopg://"):
        u = "postgresql://" + u[len("postgresql+psycopg://"):]
    elif u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://"):]
    return u

def psycopg_conninfo_from_env() -> Optional[str]:
    """
    Return a libpq-compatible conninfo/URI for psycopg.
    Accepts SQLAlchemy-style 'postgresql+psycopg://' and normalizes it.
    """
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return None
    # normalize SQLAlchemy dialect URI to plain libpq URI
    if url.startswith("postgresql+psycopg://"):
        url = "postgresql://" + url[len("postgresql+psycopg://"):]
    return url

def wait_for_db(max_attempts: int = 30, sleep_sec: float = 1.0, log=print) -> bool:
    dsn = psycopg_conninfo_from_env()
    if not dsn:
        log("[db_init] DATABASE_URL is empty; cannot wait for DB")
        return False

    log(f"[db_init] normalized DSN (redacted): {dsn_summary(dsn)}")
    for i in range(1, max_attempts + 1):
        try:
            with psycopg.connect(dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            log(f"[db_init] DB ready")
            return True
        except Exception as e:
            log(f"[db_init] waiting for db ({i}/{max_attempts})... {e}")
            time.sleep(sleep_sec)

    log("[db_init] ERROR: DB not ready after retries")
    return False
        