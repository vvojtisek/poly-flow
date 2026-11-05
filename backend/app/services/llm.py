"""OpenAI-compatible chat client for a local model (plan decision 5). No cloud fallback.

The adapter only sends what callers pass; callers keep learner data minimal (no names, no
profile ids) and treat the reply as untrusted text that must be validated before use.
"""

import ipaddress
import logging
import socket
import time
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings

log = logging.getLogger("polyflow.llm")
MAX_REPLY_CHARS = 4000


class LlmUnavailable(Exception):
    """No model configured, the endpoint is refused by policy, unreachable, or replied badly."""


@dataclass(frozen=True, slots=True)
class Reply:
    text: str
    model: str
    provider: str  # host of the endpoint, for provenance


def is_local_host(host: str) -> bool:
    """localhost, a private/link-local address, or a single-label name (a Compose service)."""
    if host in ("localhost",) or "." not in host:
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if not (addr.is_private or addr.is_loopback or addr.is_link_local):
            return False
    return True


class Llm:
    def __init__(
        self,
        base_url: str | None,
        model: str,
        *,
        api_key: str | None = None,
        timeout_s: float = 60.0,
        allow_remote: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.model = model
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.allow_remote = allow_remote
        self.transport = transport

    @property
    def configured(self) -> bool:
        return self.base_url is not None

    def _check_policy(self) -> str:
        if not self.base_url:
            raise LlmUnavailable("not_configured")
        host = urlparse(self.base_url).hostname or ""
        if not self.allow_remote and not is_local_host(host):
            raise LlmUnavailable("remote_not_allowed")
        return host

    async def chat(
        self, system: str, user: str, *, max_tokens: int = 400, temperature: float = 0.2
    ) -> Reply:
        host = self._check_policy()
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_s, transport=self.transport
            ) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions", json=body, headers=headers
                )
            r.raise_for_status()
            data = r.json()
            text = data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            log.warning("llm_failed", extra={"error": type(exc).__name__, "provider": host})
            raise LlmUnavailable("request_failed") from exc
        if not isinstance(text, str) or not text.strip():
            raise LlmUnavailable("empty_reply")
        # Learner content is never logged; only timing and provenance.
        log.info(
            "llm_reply",
            extra={
                "provider": host,
                "model": self.model,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "chars": len(text),
            },
        )
        return Reply(text=text.strip()[:MAX_REPLY_CHARS], model=self.model, provider=host)


@lru_cache
def _default() -> Llm:
    s = get_settings()
    return Llm(
        s.llm_url,
        s.llm_model,
        api_key=s.llm_api_key,
        timeout_s=s.llm_timeout_s,
        allow_remote=s.llm_allow_remote,
    )


def get_llm() -> Llm:
    return _default()
