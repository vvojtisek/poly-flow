"""Learning insights: activity calendar, weekly accuracy, mistakes and the review forecast."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.db.session import get_session
from app.main import app
from app.models import LearningEvent, LexiconItem, UserWordProgress
from app.models.learning import TaskType
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import Clock, seed_words, setup_parent


@pytest.fixture(autouse=True)
def clock():
    c = Clock()
    app.dependency_overrides[get_now] = lambda: c.now
    app.dependency_overrides[get_limiter] = lambda: MemoryAttemptLimiter()
    yield c
    app.dependency_overrides.clear()


def event(uid, item, at, *, correct, graded=True, tag=None):
    return LearningEvent(
        user_id=uid,
        lexicon_item_id=item,
        task_type=TaskType.RECOGNITION,
        attempt_no=1,
        answer="x",
        is_correct=correct,
        verdict="correct" if correct else "wrong",
        hint_used=False,
        counts_as_evidence=graded,
        policy_version="v4",
        idempotency_key=uuid.uuid4().hex,
        occurred_at=at,
        local_date=at.date(),
        result={},
        error_tag=tag,
    )


async def test_insights_aggregate_the_learners_own_events(db, client, clock):
    me = await setup_parent(client)
    uid = uuid.UUID(me["acting"]["id"])
    await seed_words("de")
    async for s in get_session():
        items = list(
            (await s.execute(select(LexiconItem.id).order_by(LexiconItem.frequency_rank))).scalars()
        )
        now = clock.now
        s.add_all(
            [
                event(uid, items[0], now, correct=True),
                event(uid, items[1], now, correct=False, tag="gender"),
                event(uid, items[1], now, correct=False, graded=False),
                event(uid, items[2], now - timedelta(days=3), correct=True),
                UserWordProgress(
                    user_id=uid,
                    lexicon_item_id=items[0],
                    introduced_at=now - timedelta(days=4),
                    next_review_at=now + timedelta(days=2),
                    passive_known=True,
                    policy_version="v4",
                ),
                UserWordProgress(
                    user_id=uid,
                    lexicon_item_id=items[1],
                    introduced_at=now - timedelta(days=4),
                    next_review_at=now - timedelta(days=1),  # overdue: due today
                    policy_version="v4",
                ),
            ]
        )
        await s.commit()
    r = await client.get("/api/v1/insights?language=de")
    assert r.status_code == 200, r.text
    out = r.json()
    today = next(d for d in out["heatmap"] if d["date"] == out["today"])
    assert today == {"date": out["today"], "graded": 2, "practice": 1}
    assert out["active_days"] == 2 and len(out["heatmap"]) == 182
    assert sum(w["answered"] for w in out["accuracy"]) == 3
    assert sum(w["correct"] for w in out["accuracy"]) == 2
    assert out["mistakes"] == [{"tag": "gender", "count": 1}]
    assert out["forecast"][0]["words"] == 1 and out["forecast"][2]["words"] == 1
    assert out["funnel"]["introduced"] == 2 and out["funnel"]["passive"] == 1
    # Another language sees none of it.
    other = (await client.get("/api/v1/insights?language=fr")).json()
    assert other["active_days"] == 0 and other["funnel"]["introduced"] == 0
