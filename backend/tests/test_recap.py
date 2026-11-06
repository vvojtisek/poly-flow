"""Weekly recap: this week against the last, hard words, due reviews, one suggestion."""

import uuid
from datetime import timedelta

from sqlalchemy import select

from app.db.session import get_session
from app.domain.recap import Week, suggest, trend
from app.models import LexiconItem, UserWordProgress
from tests.helpers import seed_words, setup_parent
from tests.test_insights import clock, event  # noqa: F401  (fixture and event builder)


def _w(**kw) -> Week:
    base = dict(active_days=3, graded=10, correct=8, practice=2, introduced=6, newly_known=2)
    return Week(**{**base, **kw})


def test_accuracy_is_unknown_without_graded_answers():
    assert _w(graded=0, correct=0).accuracy is None
    assert _w().accuracy == 0.8


def test_trend():
    assert trend(0.9, 0.7) == "up" and trend(0.6, 0.8) == "down" and trend(0.8, 0.78) == "same"
    assert trend(None, 0.8) is None and trend(0.8, None) is None


def test_suggest_order():
    assert suggest(_w(), due_now=4, hard_words=2) == "check_due"
    assert suggest(_w(active_days=0), due_now=0, hard_words=0) == "start_small"
    assert suggest(_w(), due_now=0, hard_words=1) == "fix_mistakes"
    assert suggest(_w(introduced=2), due_now=0, hard_words=0) == "new_lesson"
    assert suggest(_w(), due_now=0, hard_words=0) == "keep_going"


async def test_recap_api(db, client, clock):  # noqa: F811
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
                event(uid, items[1], now, correct=False),
                event(uid, items[1], now - timedelta(days=1), correct=False),
                event(uid, items[2], now - timedelta(days=2), correct=True, graded=False),
                event(uid, items[0], now - timedelta(days=9), correct=False),  # the week before
                UserWordProgress(
                    user_id=uid,
                    lexicon_item_id=items[0],
                    introduced_at=now - timedelta(days=2),
                    known_since_at=now - timedelta(days=1),
                    next_review_at=now - timedelta(hours=1),
                    policy_version="v4",
                ),
                UserWordProgress(
                    user_id=uid,
                    lexicon_item_id=items[1],
                    introduced_at=now - timedelta(days=20),
                    next_review_at=now + timedelta(days=3),
                    policy_version="v4",
                ),
            ]
        )
        await s.commit()
    r = await client.get("/api/v1/insights/recap?language=de")
    assert r.status_code == 200, r.text
    out = r.json()
    w = out["this_week"]
    assert (w["active_days"], w["graded"], w["correct"], w["practice"]) == (3, 3, 1, 1)
    assert w["introduced"] == 1 and w["newly_known"] == 1
    assert abs(w["accuracy"] - 1 / 3) < 1e-9
    assert out["last_week"]["graded"] == 1 and out["last_week"]["accuracy"] == 0
    assert out["accuracy_trend"] == "up"
    assert [h["misses"] for h in out["hard_words"]] == [2]
    assert out["due_now"] == 1 and out["due_next_7_days"] == 2
    assert out["suggestion"] == "check_due"
    assert "from" in out and out["to"] >= out["from"]
    other = (await client.get("/api/v1/insights/recap?language=fr")).json()
    assert other["this_week"]["accuracy"] is None and other["suggestion"] == "start_small"
