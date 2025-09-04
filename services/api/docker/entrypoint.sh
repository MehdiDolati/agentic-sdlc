#!/usr/bin/env sh

# entrypoint.sh (top of file)
[ "${DEBUG_ENTRYPOINT:-0}" = "1" ] && set -x

echo "[entrypoint] starting (uid=$(id -u) gid=$(id -g))"
echo "[entrypoint] DATABASE_URL (raw, redacted): $(printf '%s' "${DATABASE_URL:-<unset>}" | sed -E 's#(://[^:]+:)[^@]+#\1****#')"
echo "[entrypoint] UVICORN_HOST=${UVICORN_HOST:-0.0.0.0}  UVICORN_PORT=${UVICORN_PORT:-8080}"
command -v psql >/dev/null 2>&1 && psql --version || echo "[entrypoint] psql not found"
python -c 'import sys,platform,os;print("[entrypoint] py",sys.version.split()[0], platform.platform(), "cwd", os.getcwd())'


set -eu

echo "[entrypoint] starting (uid=$(id -u) gid=$(id -g))"

# Optional: print normalized DSN for debug (password redacted)
# We keep logging minimal & safe:
if [ "${DATABASE_URL:-}" ]; then
  echo "[entrypoint] DATABASE_URL (raw, redacted): $(echo "$DATABASE_URL" | sed -E 's#(://[^:]+):[^@]*@#\1:****@#')"
fi

# Hand off to the db init wrapper in app.py (it logs too) or run the app directly.
# If your Dockerfile CMD runs `python -m uvicorn ...`, you can leave this script
# to just exec CMD:
exec "$@"

log() { printf "%s %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

log "[entrypoint] starting. whoami=$(whoami) pwd=$(pwd)"
log "[entrypoint] ls -la /app && ls -la /app/services/api && ls -la /app/services/api/docker"
ls -la /app || true
ls -la /app/services/api || true
ls -la /app/services/api/docker || true

# Show env and DB URL (mask password if present)
RAW_URL="${DATABASE_URL:-}"
MASKED_URL="$RAW_URL"
case "$RAW_URL" in
  *://*:*@*)
    # redact password between : and @
    MASKED_URL="$(printf "%s" "$RAW_URL" | sed -E 's#(://[^:]+):[^@]*@#\1:****@#')"
  ;;
esac
log "[entrypoint] DATABASE_URL(raw)=${MASKED_URL:-<empty>}"

# Print Python info and import path to verify module imports
python - <<'PY' || true
import sys, os
print("[entrypoint] python:", sys.version)
print("[entrypoint] sys.path:", sys.path)
print("[entrypoint] CWD:", os.getcwd())
try:
    import services.api.db as dbmod
    print("[entrypoint] imported services.api.db from:", dbmod.__file__)
except Exception as e:
    print("[entrypoint] FAILED to import services.api.db:", repr(e))
PY

log "[db_init] waiting for db readiness using services.api.db.psycopg_conninfo_from_env()"

i=1
while [ $i -le 30 ]; do
  if python - <<'PY'
import sys, os
from services.api.db import psycopg_conninfo_from_env
import psycopg

def redact(url: str) -> str:
    # redact password if URI
    import re
    return re.sub(r'(://[^:]+):[^@]*@', r'\1:****@', url)

try:
    dsn = psycopg_conninfo_from_env()  # normalize + return a psycopg-friendly conninfo
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
    log "[db_init] db is ready"
    break
  fi
  log "[db_init] waiting for db (${i}/30)..."
  i=$((i+1))
  sleep 1
done

if [ $i -gt 30 ]; then
  log "[db_init] ERROR: DB not ready after retries"
  # show environment again for triage
  env | sort
  exit 1
fi

# Enable app startup debug (app prints DSN summary)
export STARTUP_DEBUG=1

log "[entrypoint] exec: $*"
exec "$@"
