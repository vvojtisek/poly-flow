"""Mistake engine for words (policy v4): error tags, lesson remediation, weak spots."""

import pytest
from sqlalchemy import select

from app.db.session import get_session
from app.models import LearningEvent
from tests.helpers import csrf, seed_words
from tests.test_learning import (
    answer,
    checkable,
    child_session,
    correct_answer,
    finish,
    next_task,
    start,
    wrong_answer,
)
from tests.test_learning import overrides as overrides


@pytest.fixture
def clock(overrides):
    return overrides


GENDERED = [
    ("Hund", "NOUN", "pes", "der"),
    ("Katze", "NOUN", "kočka", "die"),
    ("Haus", "NOUN", "dům", "das"),
    ("gehen", "VERB", "jít", None),
    ("schön", "ADJ", "hezký", None),
    ("gut", "ADJ", "dobrý", None),
]


async def seed_gendered() -> None:
    from app.cli import LexiconRow, upsert_lexicon

    await upsert_lexicon(
        [
            LexiconRow(language="de", rank=i + 1, lemma=w, pos=p, translation_cs=c, gender=g)
            for i, (w, p, c, g) in enumerate(GENDERED)
        ]
    )


async def miss_everything_in_a_check(client, me, clock) -> list[str]:
    s = await checkable(client, me, clock)
    missed = []
    while (t := await next_task(client, s["id"])) is not None:
        r = await answer(client, me, t, await wrong_answer(t))
        assert r.status_code == 200
        body = r.json()
        assert body["error"] in ("meaning", "spelling")
        missed.append(t["prompt"])
    await finish(client, me, s)
    return missed


async def test_wrong_answers_are_tagged(db, client, clock):
    await seed_words()
    me = await child_session(client)
    s = await checkable(client, me, clock)
    t = await next_task(client, s["id"])
    r = (await answer(client, me, t, await wrong_answer(t))).json()
    assert r["correct"] is False and r["error"] == "meaning"
    async for db_ in get_session():
        ev = (
            await db_.execute(select(LearningEvent).where(LearningEvent.is_correct.is_(False)))
        ).scalar_one()
        assert ev.error_tag == "meaning" and ev.policy_version == "v4"


async def test_wrong_german_article_is_correct_but_tagged_gender(db, client, clock):
    await seed_gendered()
    me = await child_session(client)
    s = await start(client, me)
    while (t := await next_task(client, s["id"])) is not None:
        body = await correct_answer(t)
        if t["type"] == "recall" and t["prompt"] == "pes":
            body = {"text": "die Hund"}
        r = (await answer(client, me, t, body)).json()
        if t["type"] == "recall" and t["prompt"] == "pes":
            assert (
                r["correct"] is True and r["note"] == "de_wrong_article" and r["error"] == "gender"
            )
        elif not r["task_done"]:
            raise AssertionError(r)


async def test_missed_words_open_the_next_lesson_as_ungraded_practice(db, client, clock):
    await seed_words()
    me = await child_session(client)
    missed = await miss_everything_in_a_check(client, me, clock)
    assert missed
    s = await start(client, me)
    first = await next_task(client, s["id"])
    # Remediation comes first: a recall of a missed word, marked as review, never counted.
    assert first["is_new_item"] is False and first["type"] == "recall"
    r = (await answer(client, me, first, await correct_answer(first))).json()
    assert r["counted"] is False


async def test_weak_spots_list_unresolved_words_and_mistake_kinds(db, client, clock):
    await seed_words()
    me = await child_session(client)
    missed = await miss_everything_in_a_check(client, me, clock)
    r = await client.get("/api/v1/learning/weak-spots?language=de")
    assert r.status_code == 200, r.text
    w = r.json()
    assert len(w["words"]) == len(set(missed)) and w["window_days"] == 21
    assert all(x["errors"] >= 1 and x["tags"] for x in w["words"])
    # Each word carries its lexicon id so the dashboard can open its dictionary card and audio.
    assert len({x["item_id"] for x in w["words"]}) == len(w["words"])
    assert dict(w["tags"]).get("meaning", 0) + dict(w["tags"]).get("spelling", 0) == len(missed)
    # Answering them right in the next check resolves them.
    clock.advance(days=1)
    s = await start(client, me, mode="check")
    while (t := await next_task(client, s["id"])) is not None:
        await answer(client, me, t, await correct_answer(t))
    await finish(client, me, s)
    w = (await client.get("/api/v1/learning/weak-spots?language=de")).json()
    assert w["words"] == []
    assert csrf(me)


async def test_weak_deck_holds_exactly_the_unresolved_words(db, client, clock):
    await seed_words()
    me = await child_session(client)
    missed = await miss_everything_in_a_check(client, me, clock)
    deck = (await client.get("/api/v1/words/deck?language=de&weak=true")).json()
    weak = (await client.get("/api/v1/learning/weak-spots?language=de")).json()
    assert {c["id"] for c in deck["items"]} == {w["item_id"] for w in weak["words"]}
    assert deck["total"] == len(set(missed))
    both = await client.get("/api/v1/words/deck?language=de&weak=true&level=A1")
    assert both.status_code == 422
