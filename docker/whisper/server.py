"""Minimal STT service: POST audio, get words with per-word probabilities.

Note: `probability` is Whisper's decoder token probability, i.e. how confident the
model is in the transcription. It is a proxy for intelligibility, not a calibrated
pronunciation score.

The model is loaded from a local directory filled by `scripts/models.py fetch`
(WHISPER_MODEL_DIR/WHISPER_MODEL); the service never downloads anything itself.
Uploads are decoded in memory and never written to disk.
"""

import asyncio
import io
import json
import logging
import os
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import ctranslate2
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel, decode_audio
from starlette.formparsers import MultiPartParser

SAMPLE_RATE = 16_000
LANGUAGES = {"de", "fr", "it", "en", "cs"}


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "service": "whisper",
        }
        entry["msg"] = record.getMessage()
        entry.update(getattr(record, "fields", {}))
        return json.dumps(entry)


_handler = logging.StreamHandler()
_handler.setFormatter(_JsonFormatter())
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), handlers=[_handler])
log = logging.getLogger("whisper")


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


MODEL_NAME = os.getenv("WHISPER_MODEL", "small")
MODEL_DIR = Path(os.getenv("WHISPER_MODEL_DIR", "/models"))
MAX_UPLOAD_BYTES = _env_int("WHISPER_MAX_UPLOAD_BYTES", 5 * 1024 * 1024)
MAX_SECONDS = _env_int("WHISPER_MAX_SECONDS", 30)
CONCURRENCY = _env_int("WHISPER_CONCURRENCY", 1)
QUEUE_TIMEOUT_S = _env_float("WHISPER_QUEUE_TIMEOUT_S", 30.0)

# keep uploads within the limit in memory: Starlette spools larger parts to a temp file
MultiPartParser.spool_max_size = MAX_UPLOAD_BYTES + 1

_model: WhisperModel | None = None
_device = "cpu"
_compute_type = "int8"
_slots = asyncio.Semaphore(CONCURRENCY)


def _resolve_device() -> tuple[str, str]:
    device = os.getenv("WHISPER_DEVICE", "auto")
    if device == "auto":
        device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "auto")
    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"
    return device, compute_type


def load_model() -> WhisperModel:
    global _model, _device, _compute_type
    if _model is None:
        path = MODEL_DIR / MODEL_NAME
        if not (path / "model.bin").is_file():
            raise RuntimeError(
                f"model files missing in {path}: run `scripts/models.py fetch` "
                f"(the `models` compose service) for whisper/{MODEL_NAME}"
            )
        _device, _compute_type = _resolve_device()
        started = time.monotonic()
        _model = WhisperModel(str(path), device=_device, compute_type=_compute_type)
        log.info(
            "model loaded",
            extra={
                "fields": {
                    "model": MODEL_NAME,
                    "device": _device,
                    "compute_type": _compute_type,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                }
            },
        )
    return _model


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    load_model()  # load eagerly: fail fast on missing files, no multi-second first request
    yield


app = FastAPI(title="polyflow-whisper", lifespan=lifespan)


@app.middleware("http")
async def reject_oversized(request: Request, call_next):
    """Refuse a declared oversized body before reading it (multipart overhead allowed)."""
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_UPLOAD_BYTES + 64 * 1024:
        return JSONResponse(
            {"detail": f"audio larger than {MAX_UPLOAD_BYTES} bytes"}, 413
        )
    return await call_next(request)


@app.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "model_loaded": _model is not None,
        "model": MODEL_NAME,
        "device": _device,
        "compute_type": _compute_type,
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "max_seconds": MAX_SECONDS,
        "concurrency": CONCURRENCY,
        "queue_timeout_s": QUEUE_TIMEOUT_S,
    }


async def _read_limited(audio: UploadFile) -> bytes:
    data = await audio.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"audio larger than {MAX_UPLOAD_BYTES} bytes")
    if not data:
        raise HTTPException(422, "empty audio")
    return data


def _transcribe(
    data: bytes, language: str | None, queued_ms: int, request_id: str
) -> dict:
    try:
        samples = decode_audio(io.BytesIO(data), sampling_rate=SAMPLE_RATE)
    except Exception as exc:
        # PyAV raises several unrelated types for undecodable input.
        raise HTTPException(422, "audio could not be decoded") from exc
    duration = len(samples) / SAMPLE_RATE
    if duration > MAX_SECONDS:
        raise HTTPException(413, f"audio longer than {MAX_SECONDS} s")
    started = time.monotonic()
    segments, info = load_model().transcribe(
        samples,
        language=language,
        word_timestamps=True,
        vad_filter=True,
        beam_size=5,
    )
    words = [
        {
            "word": w.word.strip(),
            "start": w.start,
            "end": w.end,
            "probability": w.probability,
        }
        for s in segments
        for w in (s.words or [])
    ]
    elapsed_ms = round((time.monotonic() - started) * 1000)
    log.info(
        "transcribed",
        extra={
            "fields": {
                "audio_s": round(duration, 2),
                "queued_ms": queued_ms,
                "duration_ms": elapsed_ms,
                "words": len(words),
                "language": info.language,
                "request_id": request_id,
            }
        },
    )
    return {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": duration,
        "text": " ".join(w["word"] for w in words),
        "words": words,
        "processing_ms": elapsed_ms,
    }


@app.post("/v1/transcribe")
async def transcribe(
    request: Request,
    audio: Annotated[UploadFile, File()],
    language: Annotated[str | None, Form()] = None,
) -> dict:
    if language is not None and language not in LANGUAGES:
        raise HTTPException(422, "unsupported language")
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    data = await _read_limited(audio)
    queued_started = time.monotonic()
    try:
        await asyncio.wait_for(_slots.acquire(), timeout=QUEUE_TIMEOUT_S)
    except TimeoutError as exc:
        log.warning(
            "transcription busy",
            extra={
                "fields": {
                    "queue_timeout_s": QUEUE_TIMEOUT_S,
                    "request_id": request_id,
                }
            },
        )
        raise HTTPException(429, "transcription busy") from exc
    try:
        # transcription is blocking CPU/GPU work: keep it off the event loop
        queued_ms = round((time.monotonic() - queued_started) * 1000)
        return await run_in_threadpool(
            _transcribe, data, language, queued_ms, request_id
        )
    finally:
        _slots.release()
