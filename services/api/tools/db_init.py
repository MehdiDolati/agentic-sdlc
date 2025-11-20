# services/api/tools/db_init.py
import os, time, sys, re
from pathlib import Path

def _is_sqlite(url: str) -> bool:
    return bool(url) and url.strip().lower().startswith("sqlite:")
    
DSN = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/appdb")
RETRIES = int(os.getenv("DB_INIT_RETRIES", "30"))
DELAY = float(os.getenv("DB_INIT_DELAY", "1.0"))

def ensure_all_schemas():
    """Ensure all database schemas using SQLAlchemy definitions"""
    try:
        # Add the project root to Python path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from services.api.core.shared import _create_engine
        from services.api.core.repos import (
            ensure_projects_schema, ensure_plans_schema, ensure_runs_schema,
            ensure_notes_schema, ensure_history_schema, ensure_features_schema,
            ensure_priority_changes_schema
        )
        
        engine = _create_engine(DSN)
        ensure_projects_schema(engine)
        ensure_plans_schema(engine)
        ensure_runs_schema(engine)
        ensure_notes_schema(engine) 
        ensure_history_schema(engine)
        ensure_features_schema(engine)
        ensure_priority_changes_schema(engine)
        print("[db_init] all schemas ensured via SQLAlchemy")
        
    except Exception as e:
        print(f"[db_init] failed to ensure schemas via SQLAlchemy: {e}")
        # Fallback to basic SQL for minimal functionality
        return f"""
CREATE TABLE IF NOT EXISTS projects(
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS plans(
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  request TEXT NOT NULL,
  owner TEXT NOT NULL,
  artifacts JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'new',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""
    return None

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

    # Postgres: wait for readiness and ensure schema
    try:
        import psycopg  # type: ignore
    except Exception as e:
        print(f"[db_init] ERROR: psycopg not available for non-sqlite DSN: {e!r}", file=sys.stderr)
        sys.exit(1)
    
    for i in range(1, RETRIES + 1):
        try:
            # First ensure connection is working
            with psycopg.connect(DSN) as conn, conn.cursor() as cur:
                cur.execute("SELECT 1")
                conn.commit()
            
            # Then ensure schemas using SQLAlchemy
            fallback_sql = ensure_all_schemas()
            if fallback_sql:
                # SQLAlchemy failed, use fallback SQL
                with psycopg.connect(DSN) as conn, conn.cursor() as cur:
                    cur.execute(fallback_sql)
                    conn.commit()
                print("[db_init] database ready and basic schema ensured via fallback SQL")
            else:
                print("[db_init] database ready and schema ensured via SQLAlchemy")
            return
        except Exception as e:
            print(f"[db_init] waiting for db ({i}/{RETRIES})... {e}")
            time.sleep(DELAY)
    print("[db_init] ERROR: DB not ready after retries", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    run()