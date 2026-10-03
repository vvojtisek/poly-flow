import logging
from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.core.config import get_settings

log = logging.getLogger("polyflow.worker")


async def startup(ctx: dict[str, Any]) -> None:
    log.info("worker_started")


async def shutdown(ctx: dict[str, Any]) -> None:
    log.info("worker_stopped")


async def ping(ctx: dict[str, Any]) -> str:
    return "pong"


class WorkerSettings:
    functions: ClassVar[list] = [ping]
    # cron_jobs: nightly ingestion, decay sweep, audio batch (to be added)
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
