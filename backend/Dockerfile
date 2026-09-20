# SatQuery AI backend. Build from the repository root (imports are absolute: backend.app...):
#   docker build -f backend/Dockerfile -t satquery-backend .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so code edits do not invalidate the pip layer.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend ./backend

# Run unprivileged; /data holds the SQLite database, uploads, overlays and reports.
RUN useradd --system --uid 10001 satquery \
    && mkdir -p /data \
    && chown satquery /data
USER satquery

# Container-specific defaults. Every other SATQUERY_* tunable keeps its documented default
# (see .env.example) and can be overridden at run time without rebuilding.
ENV SATQUERY_HOST=0.0.0.0 \
    SATQUERY_PORT=8000 \
    SATQUERY_STORAGE_DIR=/data

VOLUME /data
EXPOSE 8000

# Healthy only when the session database opens; the app migrates it at startup.
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD ["python", "backend/docker_healthcheck.py"]

CMD ["sh", "-c", "exec uvicorn backend.app.main:app --host \"$SATQUERY_HOST\" --port \"$SATQUERY_PORT\""]
