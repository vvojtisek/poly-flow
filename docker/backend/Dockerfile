# syntax=docker/dockerfile:1.7
# Build context: ./backend. Targets: `api` (FastAPI) and `worker` (ARQ) share one image base.

# Override PYTHON_IMAGE to use a registry mirror (e.g. mirror.gcr.io/library/python:3.12-slim).
ARG PYTHON_IMAGE=python:3.12-slim

# ---- builder: resolve locked deps into a self-contained venv ----
FROM ${PYTHON_IMAGE} AS builder
RUN pip install --no-cache-dir uv==0.8.17
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /src
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---- base runtime: no build tooling, non-root ----
FROM ${PYTHON_IMAGE} AS base
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app app \
    && mkdir -p /data/audio && chown app:app /data/audio  # a fresh named volume copies this owner
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app data ./data
COPY --chown=app:app app ./app
# Build provenance (scripts/build-info.sh). Last, so a new commit only rebuilds this layer.
ARG POLYFLOW_GIT_SHA=unknown
ARG POLYFLOW_GIT_BRANCH=unknown
ARG POLYFLOW_BUILD_TIME=
ENV POLYFLOW_GIT_SHA=${POLYFLOW_GIT_SHA} \
    POLYFLOW_GIT_BRANCH=${POLYFLOW_GIT_BRANCH} \
    POLYFLOW_BUILD_TIME=${POLYFLOW_BUILD_TIME}
LABEL org.opencontainers.image.revision=${POLYFLOW_GIT_SHA}
USER app

FROM base AS api
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
# Keep idle connections open longer than the frontend proxy reuses them; at uvicorn's default
# 5 s a reused socket can be closed mid-request ("socket hang up").
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--proxy-headers", \
     "--timeout-keep-alive", "75"]

FROM base AS worker
CMD ["python", "-m", "app.workers"]
