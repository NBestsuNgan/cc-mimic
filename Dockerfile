FROM python:3.12-slim

WORKDIR /srv

# Dependencies first so code edits don't bust the layer cache.
# Every wheel resolves prebuilt for arm64 (Oracle's free tier is Ampere), so no build tools.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The agent executes model-authored tool calls: never as root, and never able to
# write its own source. Only the workspace volume is writable.
RUN useradd --create-home --uid 10001 agent \
    && mkdir -p /data/workspace \
    && chown -R agent:agent /data \
    && chmod -R a-w /srv
USER agent

ENV WORKSPACE_DIR=/data/workspace \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/openapi.json')"

# --workers 1 is required: sessions live in this process's memory (see app.py).
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
