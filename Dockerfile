# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libffi-dev gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data/backups /data/logs

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app /data \
    && chmod +x /app/docker-entrypoint.sh

# Stay root at container start: Railway mounts the persistent volume at
# /data fresh (root-owned) on every deploy, which would otherwise make
# it unwritable by "appuser". The entrypoint fixes /data ownership as
# root, then drops to "appuser" via gosu before running the app.

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/health',timeout=5)" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-m", "src.main"]
