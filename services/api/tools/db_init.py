# services/api/tools/db_init.py
import os, time, sys, re
from pathlib import Path

def _is_sqlite(url: str) -> bool:
    return bool(url) and url.strip().lower().startswith("sqlite:")
    
DSN = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/appdb")
RETRIES = int(os.getenv("DB_INIT_RETRIES", "30"))
DELAY = float(os.getenv("DB_INIT_DELAY", "1.0"))

SQL = """
CREATE TABLE IF NOT EXISTS projects(
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS runs(
  id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  manifest_path TEXT,
  log_path TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

def run():
    # SQLite: no network wait; let the app's SQLAlchemy create schema on first use
    if _is_sqlite(DSN):
        try:
            # best-effort to ensure the sqlite file's parent dir exists
            m = re.match(r"sqlite:(?P<slashes>/+)(?P<path>.*)", DSN.strip())
            if m:
                # normalize absolute path for sqlite:////abs/path.db
                path = Path("/" * max(1, len(m.group("slashes") or "")) + (m.group("path") or ""))
                path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        print("[db_init] sqlite detected; skipping DB wait (SQLAlchemy will ensure schema)")
        return

    # Postgres: wait for readiness and ensure minimal schema
    try:
        import psycopg  # type: ignore
    except Exception as e:
        print(f"[db_init] ERROR: psycopg not available for non-sqlite DSN: {e!r}", file=sys.stderr)
        sys.exit(1)
    
    for i in range(1, RETRIES + 1):
        try:
            with psycopg.connect(DSN) as conn, conn.cursor() as cur:
                cur.execute(SQL)
                conn.commit()
            print("[db_init] database ready and schema ensured")
            return
        except Exception as e:
            print(f"[db_init] waiting for db ({i}/{RETRIES})... {e}")
            time.sleep(DELAY)
    print("[db_init] ERROR: DB not ready after retries", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    run()