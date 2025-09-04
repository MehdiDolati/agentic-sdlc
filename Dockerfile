# Small + secure base
FROM python:3.11-slim AS base

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
# - psycopg (pure Python wheel) covers Postgres client
RUN pip install --upgrade pip \
    && pip install -r services/api/requirements.txt

# Copy the rest of the source
COPY . .

# Ensure entrypoint has Unix line endings and is executable (CI-safe)
RUN set -eux; \
  sed -i 's/\r$//' /app/services/api/docker/entrypoint.sh; \
  chmod 0755 /app/services/api/docker/entrypoint.sh

# normalize line endings and make entrypoint executable
RUN set -eux; \
	sed -i 's/\r$//' services/api/docker/entrypoint.sh && \
    chmod +x services/api/docker/entrypoint.sh

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app

USER app

EXPOSE 8080
ENV PORT=8080

# NOTE:
# Root filesystem will be made read-only via docker-compose.
ENTRYPOINT ["/usr/bin/tini","-g","--","/app/services/api/docker/entrypoint.sh"]
CMD ["python","-m","uvicorn","services.api.app:app","--host","0.0.0.0","--port","8080"]
