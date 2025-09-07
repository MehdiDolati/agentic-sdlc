#!/usr/bin/env bash
set -eu

# Enable extra logging with DEBUG_ENTRYPOINT=1
[ "${DEBUG_ENTRYPOINT:-0}" = "1" ] && set -x

echo "[entrypoint] starting (uid=$(id -u) gid=$(id -g))"

# Redact password in logs
if [ "${DATABASE_URL:-}" ]; then
  masked="$(printf '%s' "$DATABASE_URL" | sed -E 's#(://[^:]+):[^@]*@#\1:****@#')"
  echo "[entrypoint] DATABASE_URL (raw, redacted): $masked"
else
  echo "[entrypoint] DATABASE_URL is not set"
fi

python - <<'PY' || true
import sys, platform, os
print("[entrypoint] py", sys.version.split()[0], platform.platform(), "cwd", os.getcwd())
PY

echo "[db_init] waiting for db readiness using services.api.db.psycopg_conninfo_from_env()"

i=1
while [ $i -le 30 ]; do
  if python - <<'PY'
import sys
from services.api.db import psycopg_conninfo_from_env
import psycopg

def redact(url: str) -> str:
    import re
    return re.sub(r'(://[^:]+):[^@]*@', r'\1:****@', url)

try:
    dsn = psycopg_conninfo_from_env()
    print("[db_init] normalized DSN ->", redact(str(dsn)))
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            print("[db_init] SELECT 1 ->", cur.fetchone())
    sys.exit(0)
except Exception as e:
    print("[db_init] connect failed:", repr(e))
    sys.exit(1)
PY
  then
    echo "[db_init] database ready and schema ensured"
    break
  fi
  echo "[db_init] waiting for db (${i}/30)..."
  i=$((i+1))
  sleep 1
done

if [ $i -gt 30 ]; then
  echo "[db_init] ERROR: DB not ready after retries"
  env | sort
  exit 1
fi

echo "[entrypoint] exec: $*"
exec "$@"
