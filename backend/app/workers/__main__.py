"""`python -m app.workers`: ARQ worker with JSON logging (the `arq` CLI installs its own)."""

from arq import run_worker

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.workers.settings import WorkerSettings

if __name__ == "__main__":
    configure_logging(get_settings().log_level)
    run_worker(WorkerSettings)  # type: ignore[arg-type]
