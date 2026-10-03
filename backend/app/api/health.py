import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_engine

log = logging.getLogger("polyflow.health")
router = APIRouter(tags=["health"])


class Liveness(BaseModel):
    status: Literal["ok"] = "ok"


class DependencyCheck(BaseModel):
    ok: bool
    error: str | None = None


class Readiness(BaseModel):
    status: Literal["ready", "unready"]
    checks: dict[str, DependencyCheck]


@router.get("/healthz", response_model=Liveness)
async def healthz() -> Liveness:
    """Liveness: process is up. No dependency calls."""
    return Liveness()


async def _check_db() -> None:
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))


async def _check_redis() -> None:
    client = Redis.from_url(get_settings().redis_url)
    try:
        await client.ping()
    finally:
        await client.aclose()


async def _run(name: str, fn) -> tuple[str, DependencyCheck]:
    try:
        await asyncio.wait_for(fn(), timeout=get_settings().readiness_timeout_s)
        return name, DependencyCheck(ok=True)
    except Exception as exc:
        log.warning("readiness_check_failed", extra={"dependency": name, "error": repr(exc)})
        return name, DependencyCheck(ok=False, error=type(exc).__name__)


@router.get("/readyz", response_model=Readiness)
async def readyz(response: Response) -> Readiness:
    """Readiness: Postgres and Redis reachable."""
    results = dict(await asyncio.gather(_run("postgres", _check_db), _run("redis", _check_redis)))
    ready = all(c.ok for c in results.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return Readiness(status="ready" if ready else "unready", checks=results)
