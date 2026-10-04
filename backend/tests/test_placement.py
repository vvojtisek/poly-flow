"""Placement test: the adaptive estimate (pure) and the flow through the API."""

import math
import random

import pytest
from sqlalchemy import select

from app.cli import LexiconRow, upsert_lexicon
from app.db.session import get_session
from app.domain.placement import PLACEMENT, estimate, is_finished, next_rank, p_correct
from app.models import LanguagePlacement, LearningEvent, LexiconItem, UserWordProgress
from tests.helpers import csrf, login, make_child, setup_parent
from tests.test_learning import key, next_task, overrides  # noqa: F401  (fixture)

# ---------------------------------------------------------------- domain


def simulate(level: float, ceiling: int, *, noisy: bool = False, seed: int = 1):
    """A learner who knows every word ranked <= level (or, noisy, as the model assumes)."""
    rng = random.Random(seed)
    answers: list[tuple[int, bool]] = []
    asked: set[int] = set()
    while (target := next_rank(answers, ceiling)) is not None:
        rank = min(
            (r for r in range(1, ceiling + 1) if r not in asked), key=lambda r: abs(r - target)
        )
        asked.add(rank)
        if noisy:
            ok = rng.random() < p_correct(rank, math.log(max(level, 0.5)))
        else:
            ok = rank <= level
        answers.append((rank, ok))
    return answers


def test_first_question_is_mid_scale():
    # The middle of the frequency scale on a log axis: rank ~70 of 5000, ~10 of 100.
    assert 50 <= next_rank([], 5000) <= 100
    assert 7 <= next_rank([], 100) <= 14


@pytest.mark.parametrize("level", [15, 40, 300, 1000, 2500])
@pytest.mark.parametrize("noisy", [False, True])
def test_estimate_converges_within_bounds(level, noisy):
    answers = simulate(level, 5000, noisy=noisy)
    assert PLACEMENT.min_items <= len(answers) <= PLACEMENT.max_items
    est = estimate(answers, 5000)
    assert est is not None
    assert est.low <= est.level <= est.high
    assert level / 1.6 <= est.level <= level * 1.6


def test_beginner_stops_at_minimum_and_places_at_zero():
    answers = simulate(0, 5000)
    assert len(answers) == PLACEMENT.min_items
    assert estimate(answers, 5000).level == 0


def test_learner_beyond_the_lexicon_is_placed_at_the_ceiling():
    answers = simulate(20000, 100)
    assert len(answers) == PLACEMENT.min_items
    est = estimate(answers, 100)
    assert est.level == 100 and est.at_ceiling


def test_too_few_answers_place_nobody():
    answers = simulate(40, 100)[: PLACEMENT.min_items - 1]
    assert estimate(answers, 100) is None
    assert not is_finished(answers, 100)


def test_never_asks_beyond_the_lexicon():
    assert next_rank([], 0) is None
    for _ in range(PLACEMENT.max_items):
        assert 1 <= next_rank([(1, True)] * 3, 30) <= 30


# ---------------------------------------------------------------- API

N_WORDS = 60
KNOWS_UP_TO = 25


async def seed_ranked(n: int = N_WORDS, flagged: frozenset[int] = frozenset()) -> None:
    await upsert_lexicon(
        [
            LexiconRow(
                language="de",
                rank=r,
                lemma=f"wort{r}",
                pos="NOUN",
                translation_cs=f"význam {r}",
                content_flags=["violence"] if r in flagged else [],
            )
            for r in range(1, n + 1)
        ]
    )


def rank_of(task: dict) -> int:
    return int(task["prompt"].removeprefix("wort"))


async def take_test(client, me, knows_up_to: int, *, stop_after: int | None = None) -> dict:
    r = await client.post(
        "/api/v1/learning/sessions", json={"language": "de", "mode": "placement"}, headers=csrf(me)
    )
    assert r.status_code == 200, r.text
    s = r.json()["session"]
    assert s["mode"] == "placement"
    asked = 0
    while (t := await next_task(client, s["id"])) is not None:
        assert t["type"] == "recognition" and t["total"] == PLACEMENT.max_items
        rank = rank_of(t)
        if rank <= knows_up_to:
            choice = next(o["id"] for o in t["options"] if o["text"] == f"význam {rank}")
            r = await client.post(
                f"/api/v1/learning/tasks/{t['id']}/answer",
                json={"idempotency_key": key(), "choice": choice},
                headers=csrf(me),
            )
        else:  # "Nevím"
            r = await client.post(
                f"/api/v1/learning/tasks/{t['id']}/reveal",
                json={"idempotency_key": key()},
                headers=csrf(me),
            )
        assert r.status_code == 200, r.text
        assert r.json()["task_done"] and r.json()["counted"] == (rank <= knows_up_to)
        asked += 1
        if stop_after and asked >= stop_after:
            break
    r = await client.post(f"/api/v1/learning/sessions/{s['id']}/complete", headers=csrf(me))
    assert r.status_code == 200
    return r.json()


async def progress_rows() -> dict[int, UserWordProgress]:
    async for db in get_session():
        rows = (
            await db.execute(
                select(LexiconItem.frequency_rank, UserWordProgress).join(
                    UserWordProgress, UserWordProgress.lexicon_item_id == LexiconItem.id
                )
            )
        ).all()
    return dict(rows)


async def test_offered_until_decided(db, client):
    await seed_ranked()
    me = await setup_parent(client)
    info = (await client.get("/api/v1/learning/placement?language=de")).json()
    assert info["ceiling"] == N_WORDS and info["placement"] is None
    assert (await client.get("/api/v1/learning/progress?language=de")).json()["placement"] is None

    for _ in range(2):  # idempotent
        r = await client.post(
            "/api/v1/learning/placement/skip", json={"language": "de"}, headers=csrf(me)
        )
        assert r.status_code == 204
    progress = (await client.get("/api/v1/learning/progress?language=de")).json()
    assert progress["placement"]["status"] == "skipped"
    assert progress["introduced"] == 0  # skipping changes no word


async def test_placement_sets_level_without_assuming_knowledge(db, client, overrides):  # noqa: F811
    await seed_ranked()
    me = await setup_parent(client)
    done = await take_test(client, me, KNOWS_UP_TO)
    summary = done["summary"]
    assert summary["placed"] and summary["ceiling"] == N_WORDS
    level = summary["level"]
    assert KNOWS_UP_TO / 1.6 <= level <= KNOWS_UP_TO * 1.6

    rows = await progress_rows()
    async for s in get_session():
        events = (await s.execute(select(LearningEvent))).scalars().all()
    asked_right = {e.lexicon_item_id for e in events if e.counts_as_evidence}
    asked_wrong = {e.lexicon_item_id for e in events if not e.counts_as_evidence}
    assert asked_right and len(events) == summary["asked"]
    for rank, p in rows.items():
        assert not p.passive_known and not p.active_known  # nothing known by assumption
        if p.lexicon_item_id in asked_right:
            assert p.correct_count == 1 and p.introduced_by == "placement"
            assert p.next_review_at > overrides.now  # checked again like any first success
        elif p.lexicon_item_id in asked_wrong:
            assert p.introduced_at is None  # taught in a lesson
        elif rank <= level:
            # Not asked, below the level: skips the lesson, waits in Ověření to be confirmed.
            assert p.introduced_by == "placement" and p.next_review_at == overrides.now
            assert p.correct_count == 0 and p.state.value == "NEW"
    queued = sum(1 for p in rows.values() if p.introduced_by == "placement" and not p.correct_count)
    assert summary["queued"] == queued

    progress = (await client.get("/api/v1/learning/progress?language=de")).json()
    assert progress["placement"]["status"] == "placed"
    assert progress["placement"]["level"] == level
    assert progress["known"] == 0

    # Lessons continue with words the test did not cover as known: none at or below the level
    # that the learner got right or that waits in Ověření.
    r = await client.post(
        "/api/v1/learning/sessions", json={"language": "de", "mode": "learn"}, headers=csrf(me)
    )
    lesson_ranks = {int(w["lemma"].removeprefix("wort")) for w in r.json()["session"]["words"]}
    for rank in lesson_ranks:
        assert rank > level or rows[rank].lexicon_item_id in asked_wrong


async def test_check_miss_sends_a_placed_word_back_to_lessons(db, client, overrides):  # noqa: F811
    await seed_ranked()
    me = await setup_parent(client)
    await take_test(client, me, KNOWS_UP_TO)
    # Ověření asks lesson-taught words first, then the placed ones; miss everything.
    r = await client.post(
        "/api/v1/learning/sessions", json={"language": "de", "mode": "check"}, headers=csrf(me)
    )
    s = r.json()["session"]
    while (t := await next_task(client, s["id"])) is not None:
        r = await client.post(
            f"/api/v1/learning/tasks/{t['id']}/reveal",
            json={"idempotency_key": key()},
            headers=csrf(me),
        )
        assert r.status_code == 200
        prompt_rank = rank_of(t)
        p = (await progress_rows())[prompt_rank]
        assert p.introduced_at is None and p.introduced_by is None and p.next_review_at is None
        assert p.error_count == 1


async def test_stopping_early_places_nobody_but_keeps_answers(db, client):
    await seed_ranked()
    me = await setup_parent(client)
    done = await take_test(client, me, N_WORDS, stop_after=3)
    assert done["summary"]["placed"] is False and done["summary"]["asked"] == 3
    async for s in get_session():
        assert (await s.execute(select(LanguagePlacement))).first() is None
        evidence = (
            await s.execute(select(LearningEvent).where(LearningEvent.counts_as_evidence))
        ).all()
    assert len(evidence) == 3  # three first-try answers are real evidence
    rows = await progress_rows()
    assert sum(1 for p in rows.values() if p.introduced_at is not None) == 3


async def test_retake_lower_returns_unconfirmed_words(db, client):
    await seed_ranked()
    me = await setup_parent(client)
    first = (await take_test(client, me, N_WORDS))["summary"]
    assert first["at_ceiling"] and first["level"] == N_WORDS
    second = (await take_test(client, me, 5))["summary"]
    rows = await progress_rows()
    for rank, p in rows.items():
        if p.introduced_by == "placement" and p.correct_count == 0:
            assert rank <= second["level"]
    progress = (await client.get("/api/v1/learning/progress?language=de")).json()
    assert progress["placement"]["level"] == second["level"]


async def test_no_hints_in_placement(db, client):
    await seed_ranked()
    me = await setup_parent(client)
    r = await client.post(
        "/api/v1/learning/sessions", json={"language": "de", "mode": "placement"}, headers=csrf(me)
    )
    t = await next_task(client, r.json()["session"]["id"])
    r = await client.post(f"/api/v1/learning/tasks/{t['id']}/hint", headers=csrf(me))
    assert r.status_code == 409 and r.json()["detail"] == "hints_disabled"


async def test_child_is_never_asked_or_given_flagged_words(db, client):
    flagged = frozenset(range(2, N_WORDS + 1, 3))
    await seed_ranked(flagged=flagged)
    parent = await setup_parent(client)
    await make_child(client, parent)
    child = await login(client, "eva", "4321")
    done = await take_test(client, child, N_WORDS)
    assert done["summary"]["placed"]
    async for s in get_session():
        items = (
            await s.execute(
                select(LexiconItem.frequency_rank)
                .join(UserWordProgress, UserWordProgress.lexicon_item_id == LexiconItem.id)
                .where(UserWordProgress.introduced_at.is_not(None))
            )
        ).scalars()
        assert not set(items) & flagged


async def test_nothing_to_ask_starts_no_test(db, client):
    me = await setup_parent(client)
    r = await client.post(
        "/api/v1/learning/sessions", json={"language": "de", "mode": "placement"}, headers=csrf(me)
    )
    assert r.status_code == 200 and r.json()["session"] is None


async def test_lesson_words_are_marked_as_lesson_introduced(db, client):
    await seed_ranked(8)
    me = await setup_parent(client)
    r = await client.post(
        "/api/v1/learning/sessions", json={"language": "de", "mode": "learn"}, headers=csrf(me)
    )
    sid = r.json()["session"]["id"]
    await client.post(f"/api/v1/learning/sessions/{sid}/complete", headers=csrf(me))
    async for s in get_session():
        by = set((await s.execute(select(UserWordProgress.introduced_by))).scalars())
    assert by == {"lesson"}
