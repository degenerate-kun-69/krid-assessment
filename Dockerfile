# ── Krid AI — WhatsApp Orchestrator ──────────────────────────────────────────
# Single-image Dockerfile: backend (FastAPI) + static frontend served together.
#
# Build:  docker build -t krid-ai .
# Run:    docker run -p 8080:8080 --env-file .env krid-ai
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install Python dependencies first (layer-cached when code changes, not deps)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY app/ ./app/

# Copy frontend static files (served by FastAPI StaticFiles mount)
COPY frontend/ ./frontend/

# Expose the port Render / Cloud Run / docker-compose will forward to
EXPOSE 8080

# Start the server
# --workers 1: keeps it simple for this demo; scale up for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
