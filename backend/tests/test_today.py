"""Today's plan: ordered steps and the day's estimated time."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.db.session import get_session
from app.main import app
from app.models import LexiconItem, UserWordProgress
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import Clock, seed_words, setup_parent


@pytest.fixture(autouse=True)
def clock():
    c = Clock()
    app.dependency_overrides[get_now] = lambda: c.now
    app.dependency_overrides[get_limiter] = lambda: MemoryAttemptLimiter()
    yield c
    app.dependency_overrides.clear()


async def test_new_learner_gets_a_lesson_only(db, client):
    await setup_parent(client)
    await seed_words("de")
    out = (await client.get("/api/v1/today?language=de")).json()
    assert [s["kind"] for s in out["steps"]] == ["lesson"]
    assert out["minutes_today"] == 0 and out["goal_minutes"] == 10


async def test_due_reviews_come_before_new_words(db, client, clock):
    me = await setup_parent(client)
    await seed_words("de")
    async for s in get_session():
        items = list(
            (await s.execute(select(LexiconItem.id).order_by(LexiconItem.frequency_rank))).scalars()
        )
        uid = uuid.UUID(me["acting"]["id"])
        s.add(
            UserWordProgress(
                user_id=uid,
                lexicon_item_id=items[0],
                introduced_at=clock.now,
                next_review_at=clock.now - timedelta(hours=1),
                policy_version="v4",
            )
        )
        s.add(
            UserWordProgress(
                user_id=uid,
                lexicon_item_id=items[1],
                introduced_at=clock.now,
                next_review_at=clock.now + timedelta(hours=20),
                policy_version="v4",
            )
        )
        await s.commit()
    out = (await client.get("/api/v1/today?language=de")).json()
    assert [s["kind"] for s in out["steps"]] == ["check", "lesson"]
    assert out["steps"][0]["count"] == 1 and out["tomorrow_due"] == 1
