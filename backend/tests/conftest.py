"""Shared fixtures.

DB-backed tests need POLYFLOW_TEST_DATABASE_URL (a disposable database: the session
fixture rebuilds the schema with Alembic and every test truncates all tables).
Without it those tests are skipped; CI always sets it.
"""

import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

TEST_DB_URL = os.environ.get("POLYFLOW_TEST_DATABASE_URL")
if TEST_DB_URL:
    # Must happen before app.core.config.get_settings() is first called.
    os.environ["POLYFLOW_DATABASE_URL"] = TEST_DB_URL
os.environ.setdefault("POLYFLOW_COOKIE_SECURE", "false")

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        check=True,
        capture_output=True,
        env={**os.environ, "POLYFLOW_DATABASE_URL": TEST_DB_URL or ""},
    )


@pytest.fixture(scope="session")
def migrated_db() -> str:
    if not TEST_DB_URL:
        pytest.skip("POLYFLOW_TEST_DATABASE_URL not set")
    alembic("downgrade", "base")
    alembic("upgrade", "head")
    return TEST_DB_URL


async def _truncate_all() -> None:
    from sqlalchemy import text

    from app.db.base import Base
    from app.db.session import get_engine

    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with get_engine().begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def db(migrated_db: str) -> AsyncIterator[None]:
    import app.models  # noqa: F401  (register tables)
    from app.db.session import dispose_engine

    await _truncate_all()
    yield
    await _truncate_all()
    # Engines are bound to the event loop; each test gets a fresh one.
    await dispose_engine()


@pytest.fixture
async def client() -> AsyncIterator:
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c
