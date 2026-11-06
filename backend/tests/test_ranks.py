"""Personal mastery ranks: rules (no DB) and the API with recorded awards."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.db.session import get_session
from app.domain import ranks as r
from app.domain.enums import CefrLevel
from app.main import app
from app.models import LearningEvent, LexiconItem, UserWordProgress
from app.models.learning import TaskType
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import Clock, LexiconRow, csrf, setup_parent, upsert_lexicon


def test_start_rank_needs_nothing():
    assert r.rank_for(r.Stats()) == 1


def test_ranks_follow_words_grammar_and_badges():
    s = r.Stats(known_words=120, grammar_known=2, grammar_total=30)
    assert r.rank_for(s) == 3
    # 500 words without the A1 exam stays below rank 5.
    s = r.Stats(known_words=600, grammar_known=12, grammar_total=30, recoveries=10)
    assert r.rank_for(s) == 4
    s = r.Stats(
        known_words=600,
        grammar_known=12,
        grammar_total=30,
        recoveries=10,
        badges=frozenset({CefrLevel.A1}),
    )
    assert r.rank_for(s) == 5


def test_language_without_grammar_is_not_held_back():
    s = r.Stats(known_words=120, grammar_total=0)
    assert r.rank_for(s) == 3
    assert all(req["key"] != "grammar_known" for req in r.progress_to(r.RANKS[2], s))


def test_grammar_target_caps_at_the_units_the_language_has():
    s = r.Stats(known_words=120, grammar_known=1, grammar_total=1)
    assert r.rank_for(s) == 3


def test_a_rank_once_reached_is_kept():
    assert r.held_rank(r.Stats(), recorded=6) == 6


def test_ranks_are_cumulative_in_order():
    # Rank 4 needs recoveries; without them rank 5's other requirements do not skip it.
    s = r.Stats(
        known_words=600, grammar_known=12, grammar_total=30, badges=frozenset({CefrLevel.A1})
    )
    assert r.rank_for(s) == 3


def test_every_rank_has_a_tier_and_ten_ranks_exist():
    assert [x.number for x in r.RANKS] == list(range(1, 11))
    assert r.RANKS[-1].tier == "diamond"


def test_achievements_are_measured():
    keys = {a.key for a in r.ACHIEVEMENTS if a.earned(r.Stats(known_words=1, recoveries=1))}
    assert keys == {"first_word", "recover_1"}


# ---------------------------------------------------------------- API


@pytest.fixture(autouse=True)
def clock():
    c = Clock()
    lim = MemoryAttemptLimiter()
    app.dependency_overrides[get_now] = lambda: c.now
    app.dependency_overrides[get_limiter] = lambda: lim
    yield c
    app.dependency_overrides.clear()


async def seed_known(user_id: str, n: int, known: bool = True) -> list[uuid.UUID]:
    await upsert_lexicon(
        [
            LexiconRow(language="de", rank=i + 1, lemma=f"w{i}", pos="NOUN", translation_cs=f"s{i}")
            for i in range(n)
        ]
    )
    async for db in get_session():
        items = list(
            (
                await db.execute(select(LexiconItem.id).order_by(LexiconItem.frequency_rank))
            ).scalars()
        )
        for item in items:
            db.add(
                UserWordProgress(
                    user_id=uuid.UUID(user_id),
                    lexicon_item_id=item,
                    passive_known=known,
                    active_known=known,
                    policy_version="v4",
                )
            )
        await db.commit()
        return items
    raise AssertionError


async def test_promotion_is_recorded_once_and_survives_decay(db, client):
    me = await setup_parent(client)
    uid = me["acting"]["id"]
    await seed_known(uid, 30)
    out = (await client.get("/api/v1/ranks?language=de")).json()
    assert out["rank"] == 2 and out["unseen_rank"] == 2 and out["path"] == "hockey"
    assert "first_word" in out["unseen_achievements"]
    assert out["next"]["rank"] == 3
    assert {q["key"] for q in out["next"]["requirements"]} == {"known_words"}  # no grammar pack
    r1 = await client.post("/api/v1/ranks/seen", json={"language": "de"}, headers=csrf(me))
    assert r1.status_code == 204
    out = (await client.get("/api/v1/ranks?language=de")).json()
    assert out["unseen_rank"] is None and out["unseen_achievements"] == []
    # Decay clears the known flags: the rank stays.
    async for db_ in get_session():
        await db_.execute(update(UserWordProgress).values(passive_known=False, active_known=False))
        await db_.commit()
    out = (await client.get("/api/v1/ranks?language=de")).json()
    assert out["rank"] == 2 and out["stats"]["known_words"] == 0
    assert out["ranks"][1]["reached_at"] is not None


async def test_ranks_are_per_language(db, client):
    me = await setup_parent(client)
    await seed_known(me["acting"]["id"], 30)
    out = (await client.get("/api/v1/ranks?language=fr")).json()
    assert out["rank"] == 1


async def test_recovered_mistakes_count_once_per_word(db, client, clock):
    me = await setup_parent(client)
    uid = uuid.UUID(me["acting"]["id"])
    items = await seed_known(me["acting"]["id"], 2, known=False)

    def event(item, correct, minutes):
        at = clock.now + timedelta(minutes=minutes)
        return LearningEvent(
            user_id=uid,
            lexicon_item_id=item,
            task_type=TaskType.RECOGNITION,
            attempt_no=1,
            answer="x",
            is_correct=correct,
            verdict="correct" if correct else "wrong",
            hint_used=False,
            counts_as_evidence=True,
            policy_version="v4",
            idempotency_key=uuid.uuid4().hex,
            occurred_at=at,
            local_date=at.date(),
            result={},
        )

    async for db_ in get_session():
        db_.add_all(
            [
                event(items[0], False, 0),
                event(items[0], True, 5),
                event(items[0], True, 9),
                event(items[1], True, 1),  # right first: nothing to recover
                event(items[1], False, 2),  # missed later and not yet recovered
            ]
        )
        await db_.commit()
    out = (await client.get("/api/v1/ranks?language=de")).json()
    assert out["stats"]["recoveries"] == 1 and out["stats"]["checks_answered"] == 5


async def test_rank_path_setting_is_validated(db, client):
    me = await setup_parent(client)
    r1 = await client.patch(
        "/api/v1/me/profile", json={"settings": {"rank_path": "royal"}}, headers=csrf(me)
    )
    assert r1.status_code == 200 and r1.json()["settings"]["rank_path"] == "royal"
    r2 = await client.patch(
        "/api/v1/me/profile", json={"settings": {"rank_path": "leaderboard"}}, headers=csrf(me)
    )
    assert r2.status_code == 422
    assert (await client.get("/api/v1/ranks")).json()["path"] == "royal"
