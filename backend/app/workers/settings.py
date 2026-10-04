import logging
from datetime import UTC, datetime
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.db.session import dispose_engine, get_session
from app.services.learning import decay_sweep, prune_expired_sessions

log = logging.getLogger("polyflow.worker")


async def startup(ctx: dict[str, Any]) -> None:
    log.info("worker_started")


async def shutdown(ctx: dict[str, Any]) -> None:
    await dispose_engine()
    log.info("worker_stopped")


async def ping(ctx: dict[str, Any]) -> str:
    return "pong"


async def nightly_maintenance(ctx: dict[str, Any]) -> dict[str, int]:
    """Decay sweep + expired-session cleanup. Both are idempotent, so retries are safe."""
    now = datetime.now(UTC)
    async for db in get_session():
        decayed = await decay_sweep(db, now)
        pruned = await prune_expired_sessions(db, now)
        await db.commit()
    log.info("nightly_maintenance_done", extra={"decayed": decayed, "sessions_pruned": pruned})
    return {"decayed": decayed, "sessions_pruned": pruned}


class WorkerSettings:
    functions: ClassVar[list] = [ping, nightly_maintenance]
    # Household-local schedule; content ingestion (03:00) joins in P4.
    timezone = ZoneInfo(get_settings().default_timezone)
    cron_jobs: ClassVar[list] = [
        cron(nightly_maintenance, hour={2}, minute={30}, run_at_startup=False, unique=True),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    # Never log job results: later jobs (stories, dialogue) return user content.
    log_results = False
