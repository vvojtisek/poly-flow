import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_ctx

log = logging.getLogger("polyflow.http")

QUIET_PATHS = {"/healthz"}


class RequestLoggingMiddleware:
    """Pure-ASGI middleware: request id propagation + one structured log line per request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        rid = headers.get(b"x-request-id", b"").decode() or uuid.uuid4().hex
        token = request_id_ctx.set(rid)
        start = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message.setdefault("headers", []).append((b"x-request-id", rid.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            log.exception("unhandled_exception", extra={"path": scope["path"]})
            raise
        finally:
            if scope["path"] not in QUIET_PATHS:
                log.info(
                    "request",
                    extra={
                        "method": scope["method"],
                        "path": scope["path"],
                        "status": status,
                        "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    },
                )
            request_id_ctx.reset(token)
