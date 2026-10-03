"""Minimal STT service: POST audio, get words with per-word probabilities.

Note: `probability` is Whisper's decoder token probability, i.e. how confident the
model is in the transcription. It is a proxy for intelligibility, not a calibrated
pronunciation score.
"""

import logging
import os
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from faster_whisper import WhisperModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("whisper")

_model: WhisperModel | None = None


def model() -> WhisperModel:
    global _model
    if _model is None:
        name = os.environ["WHISPER_MODEL"]
        log.info("loading model %s", name)
        _model = WhisperModel(name, device="cpu", compute_type=os.environ["WHISPER_COMPUTE_TYPE"])
    return _model


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    model()  # load eagerly so the first request is not a multi-second stall
    yield


app = FastAPI(title="polyflow-whisper", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "model_loaded": _model is not None}


@app.post("/v1/transcribe")
async def transcribe(
    audio: Annotated[UploadFile, File()],
    language: Annotated[str | None, Form()] = None,
    initial_prompt: Annotated[str | None, Form()] = None,
) -> dict:
    if language is not None and language not in {"de", "fr", "it", "cs"}:
        raise HTTPException(422, "unsupported language")
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(audio.filename or "")[1]) as tmp:
        tmp.write(await audio.read())
        tmp.flush()
        segments, info = model().transcribe(
            tmp.name,
            language=language,
            initial_prompt=initial_prompt,
            word_timestamps=True,
            vad_filter=True,
            beam_size=5,
        )
        words = [
            {"word": w.word.strip(), "start": w.start, "end": w.end, "probability": w.probability}
            for s in segments
            for w in (s.words or [])
        ]
    return {
        "language": info.language,
        "language_probability": info.language_probability,
        "text": " ".join(w["word"] for w in words),
        "words": words,
    }
