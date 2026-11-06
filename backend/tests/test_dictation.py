"""Dictation: word-level comparison and the ungraded API."""

import uuid

import pytest
from sqlalchemy import func, select

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.cli import LexiconRow, upsert_lexicon
from app.db.session import get_session
from app.domain.dictation import compare, score
from app.main import app
from app.models import LearningEvent, LexiconItem, UserWordProgress
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import Clock, csrf, setup_parent


def verdicts(expected, typed):
    return [m.verdict for m in compare(expected, typed)]


def test_exact_sentence_scores_full():
    marks = compare("Ich gehe nach Hause.", "ich gehe nach Hause")
    assert [m.verdict for m in marks] == ["case", "ok", "ok", "ok"]
    assert score(compare("Ich gehe.", "Ich gehe")) == 1.0


def test_accents_umlauts_and_eszett_are_named():
    assert verdicts("Die Straße ist schön.", "Die Strasse ist schon") == [
        "ok",
        "accents",
        "ok",
        "accents",
    ]


def test_missing_and_extra_words():
    assert verdicts("Ich habe einen Hund.", "Ich habe Hund") == ["ok", "ok", "missing", "ok"]
    assert verdicts("Ich habe Zeit.", "Ich habe viel Zeit") == ["ok", "ok", "extra", "ok"]
    assert score(compare("Ich habe Zeit.", "Ich habe viel Zeit")) < 1


def test_wrong_word():
    assert verdicts("Wir gehen heute.", "Wir kommen heute") == ["ok", "wrong", "ok"]


@pytest.fixture(autouse=True)
def clock():
    c = Clock()
    app.dependency_overrides[get_now] = lambda: c.now
    app.dependency_overrides[get_limiter] = lambda: MemoryAttemptLimiter()
    yield c
    app.dependency_overrides.clear()


async def test_dictation_uses_only_taught_words_and_records_nothing(db, client, clock):
    me = await setup_parent(client)
    await upsert_lexicon(
        [
            LexiconRow(
                language="de",
                rank=1,
                lemma="Haus",
                translation_cs="dům",
                example="Das Haus ist groß.",
            ),
            LexiconRow(
                language="de", rank=2, lemma="gehen", translation_cs="jít", example="Wir gehen."
            ),
        ]
    )
    async for s in get_session():
        haus = (
            await s.execute(select(LexiconItem).where(LexiconItem.lemma == "Haus"))
        ).scalar_one()
        s.add(
            UserWordProgress(
                user_id=uuid.UUID(me["acting"]["id"]),
                lexicon_item_id=haus.id,
                introduced_at=clock.now,
                policy_version="v4",
            )
        )
        await s.commit()
    nxt = (await client.get("/api/v1/dictation/next?language=de")).json()
    assert nxt["pool"] == 1 and nxt["item_id"] == str(haus.id) and "sentence" not in nxt
    r = await client.post(
        "/api/v1/dictation/check",
        json={"item_id": nxt["item_id"], "text": "Das Haus ist gross"},
        headers=csrf(me),
    )
    out = r.json()
    assert out["sentence"] == "Das Haus ist groß." and out["marks"][-1]["verdict"] == "accents"
    async for s in get_session():
        assert await s.scalar(select(func.count()).select_from(LearningEvent)) == 0
    # A word without a lesson cannot be dictated.
    async for s in get_session():
        gehen = (
            await s.execute(select(LexiconItem.id).where(LexiconItem.lemma == "gehen"))
        ).scalar_one()
    r = await client.post(
        "/api/v1/dictation/check", json={"item_id": str(gehen), "text": "x"}, headers=csrf(me)
    )
    assert r.status_code == 404
