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

# normalize line endings and make entrypoint executable
RUN sed -i 's/\r$//' services/api/docker/entrypoint.sh && \
    chmod +x services/api/docker/entrypoint.sh

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app

USER app

EXPOSE 8080
ENV PORT=8080

# NOTE:
# Root filesystem will be made read-only via docker-compose.
ENTRYPOINT ["/usr/bin/tini","--","/app/services/api/docker/entrypoint.sh"]
CMD ["uvicorn", "services.api.app:app", "--host", "0.0.0.0", "--port", "8080"]