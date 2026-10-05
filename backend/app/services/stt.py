"""Speech to text through the Whisper service (docker/whisper/server.py).

The recording is forwarded as it arrived and never written to disk or logged; the service
decodes it in memory. No initial prompt is sent: suggesting the expected word would bias the
transcript toward the answer the learner is being checked on.
"""

import logging
import time
from functools import lru_cache

import httpx

from app.core.config import get_settings
from app.core.logging import request_id_ctx
from app.domain.enums import Language
from app.domain.speech import SpokenWord

log = logging.getLogger("polyflow.stt")


class SttUnavailable(Exception):
    """Whisper is unreachable or failed."""


class SttBusy(SttUnavailable):
    """Whisper is healthy but its bounded transcription queue is full."""


class SttRejected(Exception):
    """Whisper refused the recording (too long, too large, or not decodable audio)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class Stt:
    def __init__(
        self, base_url: str, timeout_s: float = 120.0, client: httpx.AsyncClient | None = None
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout_s)

    async def transcribe(
        self, language: Language, audio: bytes, content_type: str
    ) -> list[SpokenWord]:
        started = time.monotonic()
        try:
            headers = {}
            if request_id := request_id_ctx.get():
                headers["X-Request-ID"] = request_id
            resp = await self._client.post(
                f"{self._base_url}/v1/transcribe",
                data={"language": language.value},
                files={"audio": ("answer", audio, content_type)},
                headers=headers,
            )
        except httpx.HTTPError as exc:
            log.warning("stt_failed", extra={"error": type(exc).__name__})
            raise SttUnavailable("whisper_unreachable") from exc
        if resp.status_code == 413:
            raise SttRejected("audio_too_long")
        if resp.status_code == 422:
            raise SttRejected("audio_invalid")
        if resp.status_code == 429:
            raise SttBusy("whisper_busy")
        if resp.status_code != 200:
            log.warning("stt_failed", extra={"status": resp.status_code})
            raise SttUnavailable("whisper_failed")
        try:
            words = [
                SpokenWord(word=str(w["word"]), probability=float(w["probability"]))
                for w in resp.json()["words"]
            ]
        except (ValueError, KeyError, TypeError) as exc:
            raise SttUnavailable("whisper_bad_response") from exc
        log.info(
            "stt_transcribed",
            extra={
                "language": language.value,
                "bytes": len(audio),
                "words": len(words),
                "duration_ms": round((time.monotonic() - started) * 1000),
            },
        )
        return words


@lru_cache
def get_stt() -> Stt:
    settings = get_settings()
    return Stt(settings.whisper_url, settings.stt_timeout_s)
