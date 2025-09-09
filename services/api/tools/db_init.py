# services/api/tools/db_init.py
import os, time, sys
import psycopg

DSN = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/appdb")
RETRIES = int(os.getenv("DB_INIT_RETRIES", "30"))
DELAY = float(os.getenv("DB_INIT_DELAY", "1.0"))

SQL = """
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
