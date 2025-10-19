# Small + secure base
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps only if/when needed (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl tini \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better layer caching
COPY services/api/requirements.txt ./services/api/requirements.txt

# Install Python deps
# NOTE: prefer psycopg **binary** wheel unless your requirements already pin it.
# If your requirements.txt already has psycopg[binary], you can drop the extra pip install line.
RUN pip install --upgrade pip \
    && pip install -r services/api/requirements.txt \
    || true
# Ensure pg client is available in slim images:
RUN python - <<'PY'
import pkgutil, subprocess, sys
if not pkgutil.find_loader("psycopg"):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg[binary]"])
PY

# Copy the rest of the source
COPY . .

## Normalize entrypoint once (avoid duplicates)
RUN set -eux; \
    sed -i '1s/^\xEF\xBB\xBF//' services/api/docker/entrypoint.sh || true; \
    sed -i 's/\r$//' services/api/docker/entrypoint.sh || true; \
    chmod 0755 services/api/docker/entrypoint.sh

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app

USER app

EXPOSE 8080
ENV PORT=8080

ENTRYPOINT ["/usr/bin/tini","-g","--","/bin/sh","/app/services/api/docker/entrypoint.sh"]
CMD ["python","-m","uvicorn","services.api.app:app","--host","0.0.0.0","--port","8080"]
