# syntax=docker/dockerfile:1.7
# Build context: ./docker/whisper. CPU faster-whisper (CTranslate2, int8) behind a tiny HTTP API.
ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}
ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/models \
    WHISPER_MODEL=small \
    WHISPER_COMPUTE_TYPE=int8
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app app \
    && mkdir -p /models && chown app:app /models
WORKDIR /srv
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py ./
USER app
EXPOSE 9000
HEALTHCHECK --interval=30s --timeout=3s --start-period=120s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/healthz', timeout=2)"]
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9000"]
