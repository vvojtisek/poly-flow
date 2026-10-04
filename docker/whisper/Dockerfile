# syntax=docker/dockerfile:1.7
# Build context: ./docker/whisper. faster-whisper (CTranslate2) behind a tiny HTTP API.
# CPU int8 by default; --build-arg WHISPER_GPU=1 adds the CUDA 12 libraries for NVIDIA GPUs
# (run with docker-compose.gpu.yml). Models are not downloaded here: see scripts/models.py.
ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}
ARG WHISPER_GPU=0
ENV PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    WHISPER_MODEL_DIR=/models \
    WHISPER_MODEL=small \
    WHISPER_DEVICE=auto \
    WHISPER_COMPUTE_TYPE=auto \
    LD_LIBRARY_PATH=/usr/local/lib/python3.12/site-packages/nvidia/cublas/lib:/usr/local/lib/python3.12/site-packages/nvidia/cudnn/lib
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app app \
    && mkdir -p /models && chown app:app /models
WORKDIR /srv
COPY requirements.txt requirements-gpu.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$WHISPER_GPU" = "1" ]; then pip install --no-cache-dir -r requirements-gpu.txt; fi
COPY server.py ./
USER app
EXPOSE 9000
HEALTHCHECK --interval=30s --timeout=3s --start-period=180s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/healthz', timeout=2)"]
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9000"]
