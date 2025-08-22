# root-level Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install API deps first for better layer caching
COPY services/api/requirements.txt ./services/api/requirements.txt
RUN pip install --no-cache-dir -r services/api/requirements.txt

# Copy the whole repo (planner/docs/configs/tools included)
COPY . .

EXPOSE 8080
CMD ["uvicorn", "services.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
