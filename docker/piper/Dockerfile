# syntax=docker/dockerfile:1.7
# Build context: ./docker/piper. Upstream piper HTTP server (multi-voice via --data-dir).
ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}
ENV PYTHONUNBUFFERED=1 \
    PIPER_DATA_DIR=/data \
    PIPER_VOICES="de_DE-thorsten-medium fr_FR-siwis-medium it_IT-paola-medium"
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app app \
    && mkdir -p /data && chown app:app /data
RUN pip install --no-cache-dir "piper-tts[http]==1.8.0"
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh
USER app
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=120s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/voices', timeout=2)"]
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
