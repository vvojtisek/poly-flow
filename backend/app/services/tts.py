"""Text to speech through the Piper service, cached on disk.

Callers pass only server-chosen text (lexicon entries and scene lines that a session already
shows the learner); this module is not a general TTS proxy.

A cached file is keyed by the text, the voice name and a digest of the voice configuration
Piper reports, so a different voice revision is synthesized afresh instead of reusing audio
made by the old one. Files are written atomically; two requests for the same new text may
both synthesize it, and the last rename wins with identical content.
"""

import asyncio
import hashlib
import json
import logging
import os
import tempfile
import time
import unicodedata
from functools import lru_cache
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.domain.enums import Language

log = logging.getLogger("polyflow.tts")

# One voice per language. Keep in sync with PIPER_VOICES in docker/piper/Dockerfile and
# docker/models/models.spec.json (tests/test_tts.py checks the Dockerfile).
VOICES: dict[Language, str] = {
    Language.DE: "de_DE-thorsten-medium",
    Language.FR: "fr_FR-siwis-medium",
    Language.IT: "it_IT-paola-medium",
    Language.EN: "en_GB-jenny_dioco-medium",
}

CACHE_FORMAT = 1  # bump to invalidate every cached file
MAX_TEXT_CHARS = 400
MAX_AUDIO_BYTES = 10 * 1024 * 1024
VOICES_TTL_S = 300.0


class TtsUnavailable(Exception):
    """Piper is unreachable, lacks the voice, or returned something that is not audio."""


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def cache_key(voice: str, voice_digest: str, text: str) -> str:
    material = json.dumps(
        {"format": CACHE_FORMAT, "voice": voice, "voice_config": voice_digest, "text": text},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(material.encode()).hexdigest()


class Tts:
    def __init__(
        self,
        base_url: str,
        cache_dir: Path,
        timeout_s: float = 20.0,
        concurrency: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._cache_dir = cache_dir
        self._client = client or httpx.AsyncClient(timeout=timeout_s)
        self._slots = asyncio.Semaphore(concurrency)
        self._digests: dict[str, str] = {}
        self._digests_at = float("-inf")

    async def _voice_digest(self, voice: str) -> str:
        """Digest of the voice's configuration, refreshed from Piper every few minutes."""
        if time.monotonic() - self._digests_at > VOICES_TTL_S:
            try:
                resp = await self._client.get(f"{self._base_url}/voices")
                resp.raise_for_status()
                self._digests = {
                    name: hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
                    for name, config in resp.json().items()
                }
                self._digests_at = time.monotonic()
            except (httpx.HTTPError, ValueError, AttributeError) as exc:
                # Keep serving the cache with the last known digests while Piper is down.
                log.warning("tts_voices_unavailable", extra={"error": type(exc).__name__})
                if not self._digests:
                    raise TtsUnavailable("piper_unreachable") from exc
        digest = self._digests.get(voice)
        if digest is None:
            # Piper silently falls back to its default voice for an unknown name: refuse
            # instead of playing the wrong language.
            raise TtsUnavailable("voice_missing")
        return digest

    async def speech(self, language: Language, text: str) -> Path:
        """Path to a WAV file of `text` spoken in `language`, synthesizing it if needed."""
        text = normalize(text)
        if not text or len(text) > MAX_TEXT_CHARS:
            raise ValueError("text empty or too long for speech")
        voice = VOICES[language]
        key = cache_key(voice, await self._voice_digest(voice), text)
        path = self._cache_dir / key[:2] / f"{key}.wav"
        if path.is_file():
            return path
        async with self._slots:
            if path.is_file():  # synthesized while this request waited
                return path
            started = time.monotonic()
            try:
                resp = await self._client.post(
                    f"{self._base_url}/synthesize", json={"text": text, "voice": voice}
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                log.warning("tts_failed", extra={"voice": voice, "error": type(exc).__name__})
                raise TtsUnavailable("piper_failed") from exc
            audio = resp.content
            if audio[:4] != b"RIFF" or audio[8:12] != b"WAVE" or len(audio) > MAX_AUDIO_BYTES:
                log.warning("tts_bad_audio", extra={"voice": voice, "bytes": len(audio)})
                raise TtsUnavailable("piper_bad_audio")
            try:
                await asyncio.to_thread(_write_atomic, path, audio)
            except OSError as exc:  # misconfigured volume: lessons go on without sound
                log.error("tts_cache_unwritable", extra={"error": type(exc).__name__})
                raise TtsUnavailable("cache_unwritable") from exc
            log.info(
                "tts_synthesized",
                extra={
                    "voice": voice,
                    "chars": len(text),
                    "bytes": len(audio),
                    "duration_ms": round((time.monotonic() - started) * 1000),
                },
            )
        return path


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".wav")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


@lru_cache
def get_tts() -> Tts:
    settings = get_settings()
    return Tts(settings.piper_url, Path(settings.audio_cache_dir), settings.tts_timeout_s)
