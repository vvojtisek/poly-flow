"""Lesson engine end to end through the API (plan P2), with a controllable clock."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

from app.api.deps import get_limiter
from app.api.learning import get_now
from app.db.session import get_engine, get_session
from app.domain.enums import ProgressState
from app.main import app
from app.models import LearningEvent, LexiconItem, UserWordProgress
from app.services import learning as svc
from app.services.rate_limit import MemoryAttemptLimiter
from tests.helpers import WORDS, Clock, csrf, login, make_child, seed_words, setup_parent


@pytest.fixture(autouse=True)
def overrides():
    clock = Clock()
    lim = MemoryAttemptLimiter()
    app.dependency_overrides[get_now] = lambda: clock.now
    app.dependency_overrides[get_limiter] = lambda: lim
    yield clock
    app.dependency_overrides.clear()


@pytest.fixture
def clock(overrides) -> Clock:
    return overrides


def key() -> str:
    return uuid.uuid4().hex


async def child_session(client) -> dict:
    parent = await setup_parent(client)
    await make_child(client, parent)
    return await login(client, "eva", "4321")


async def start(client, me, language="de", mode="learn") -> dict | None:
    r = await client.post(
        "/api/v1/learning/sessions", json={"language": language, "mode": mode}, headers=csrf(me)
    )
    assert r.status_code == 200, r.text
    return r.json()["session"]


async def next_task(client, sid) -> dict | None:
    r = await client.get(f"/api/v1/learning/sessions/{sid}/next")
    assert r.status_code == 200, r.text
    return r.json()["task"]


async def correct_answer(task: dict) -> dict:
    """What a learner who knows the word would send."""
    async for db in get_session():
        item_id = (
            (
                await db.execute(
                    select(LexiconItem).where(
                        (LexiconItem.lemma == task["prompt"])
                        | (LexiconItem.translation_cs == task["prompt"])
                    )
                )
            )
            .scalars()
            .first()
        )
    if task["type"] == "recognition":
        idx = next(o["id"] for o in task["options"] if o["text"] == item_id.translation_cs)
        return {"choice": idx}
    return {"text": item_id.lemma}


async def wrong_answer(task: dict) -> dict:
    if task["type"] == "recognition":
        right = (await correct_answer(task))["choice"]
        return {"choice": next(o["id"] for o in task["options"] if o["id"] != right)}
    return {"text": "zzz"}


async def answer(client, me, task, body, k=None):
    r = await client.post(
        f"/api/v1/learning/tasks/{task['id']}/answer",
        json={"idempotency_key": k or key(), **body},
        headers=csrf(me),
    )
    return r


async def finish(client, me, s) -> dict:
    r = await client.post(f"/api/v1/learning/sessions/{s['id']}/complete", headers=csrf(me))
    assert r.status_code == 200
    return r.json()


async def run_session(client, me, language="de", correct=True, mode="learn") -> dict | None:
    s = await start(client, me, language, mode)
    if s is None:
        return None
    while (t := await next_task(client, s["id"])) is not None:
        body = await correct_answer(t) if correct else await wrong_answer(t)
        r = await answer(client, me, t, body)
        assert r.status_code == 200, r.text
        if not r.json()["task_done"]:
            r = await client.post(
                f"/api/v1/learning/tasks/{t['id']}/reveal",
                json={"idempotency_key": key()},
                headers=csrf(me),
            )
            assert r.status_code == 200
    return await finish(client, me, s)


async def run_lesson(client, me, language="de") -> dict:
    s = await run_session(client, me, language)
    assert s is not None
    return s


async def run_check(client, me, language="de", correct=True) -> dict | None:
    return await run_session(client, me, language, correct, mode="check")


async def checkable(client, me, clock, language="de") -> dict:
    """Learn the first words, wait for the next day, open a check."""
    await run_lesson(client, me, language)
    clock.advance(days=1)
    s = await start(client, me, language, "check")
    assert s is not None
    return s


async def progress_rows() -> dict[str, UserWordProgress]:
    async for db in get_session():
        rows = (
            await db.execute(
                select(LexiconItem.lemma, UserWordProgress).join(
                    LexiconItem, LexiconItem.id == UserWordProgress.lexicon_item_id
                )
            )
        ).all()
        return {lemma: p for lemma, p in rows}
    return {}


# ------------------------------------------------------------------ session building


async def test_empty_plan_without_lexicon(db, client):
    me = await child_session(client)
    assert await start(client, me) is None


async def test_new_lesson_meets_then_produces_words(db, client):
    await seed_words()
    me = await child_session(client)
    s = await start(client, me)
    assert s["total"] == 8 and s["remaining"] == 8  # 4 new words x (recognition, recall)
    types = []
    async for db_ in get_session():
        from app.models import LearningTask

        tasks = (
            await db_.execute(
                select(LearningTask)
                .where(LearningTask.session_id == uuid.UUID(s["id"]))
                .order_by(LearningTask.position)
            )
        ).scalars()
        types = [t.task_type.value for t in tasks]
    assert types == ["recognition"] * 4 + ["recall"] * 4
    t = await next_task(client, s["id"])
    assert t["type"] == "recognition" and t["prompt"] == "der"  # most frequent first
    assert "correct" not in str(t) and len(t["options"]) == 4


async def test_resume_returns_same_lesson(db, client):
    await seed_words()
    me = await child_session(client)
    s1 = await start(client, me)
    s2 = await start(client, me)
    assert s1["id"] == s2["id"]
    cur = (await client.get("/api/v1/learning/sessions/current?language=de")).json()["session"]
    assert cur["id"] == s1["id"]


async def test_concurrent_start_creates_one_lesson(db, client):
    await seed_words()
    me = await child_session(client)
    results = await asyncio.gather(*(start(client, me) for _ in range(4)))
    assert len({r["id"] for r in results}) == 1


# ------------------------------------------------------------------ learning (Lekce)


async def test_lesson_wrong_answer_shows_the_right_one_and_retries(db, client):
    await seed_words()
    me = await child_session(client)
    s = await start(client, me)
    t = await next_task(client, s["id"])
    r = (await answer(client, me, t, await wrong_answer(t))).json()
    assert r["correct"] is False and r["can_retry"] and r["expected"] == "ten"
    r = (await answer(client, me, t, await correct_answer(t))).json()
    assert r["correct"] and r["task_done"] and r["counted"] is False and r["attempts"] == 2
    p = (await progress_rows())["der"]
    # Practice is exposure only: no errors, no schedule, not introduced until the lesson ends.
    assert p.error_count == 0 and p.correct_count == 0 and p.state == ProgressState.NEW
    assert p.next_review_at is None and p.introduced_at is None


async def test_lesson_never_counts_as_evidence(db, client):
    await seed_words()
    me = await child_session(client)
    summary = await run_lesson(client, me)
    assert summary["mode"] == "learn" and summary["summary"]["first_try_correct"] == 8
    rows = await progress_rows()
    assert all(p.correct_count == 0 and not p.passive_known for p in rows.values())
    async with get_engine().connect() as conn:
        counted = (
            await conn.execute(
                select(func.count())
                .select_from(LearningEvent)
                .where(LearningEvent.counts_as_evidence.is_(True))
            )
        ).scalar_one()
    assert counted == 0


async def test_finished_lesson_introduces_words_for_tomorrow(db, client, clock):
    await seed_words()
    me = await child_session(client)
    await run_lesson(client, me)
    p = (await progress_rows())["der"]
    assert p.introduced_at == clock.now and p.state == ProgressState.LEARNING
    # 08:00 UTC on 5 Oct is 10:00 in Prague; the next local day starts at 22:00 UTC.
    assert p.next_review_at == datetime(2026, 10, 5, 22, 0, tzinfo=UTC)
    assert await start(client, me, mode="check") is None  # not the same day
    nxt = await start(client, me)  # the next lesson brings the next words
    assert nxt is not None and nxt["total"] == 4


async def test_lesson_hints_are_free(db, client):
    await seed_words()
    me = await child_session(client)
    s = await start(client, me)
    t = await next_task(client, s["id"])
    h = await client.post(f"/api/v1/learning/tasks/{t['id']}/hint", headers=csrf(me))
    assert h.status_code == 200 and len(h.json()["options"]) == 2
    r = (await answer(client, me, h.json(), await correct_answer(t))).json()
    assert r["correct"] and r["counted"] is False


async def test_recall_hint_shows_prefix(db, client):
    await seed_words(words=[("Haus", "NOUN", "dům")])
    me = await child_session(client)
    s = await start(client, me)
    t = await next_task(client, s["id"])
    assert t["type"] == "recall"  # single word: no distractors for recognition
    h1 = (await client.post(f"/api/v1/learning/tasks/{t['id']}/hint", headers=csrf(me))).json()
    h2 = (await client.post(f"/api/v1/learning/tasks/{t['id']}/hint", headers=csrf(me))).json()
    assert h1["hint"] == "H…" and h2["hint"] == "Ha…"


async def test_lesson_reveal_has_no_consequence(db, client):
    await seed_words()
    me = await child_session(client)
    s = await start(client, me)
    t = await next_task(client, s["id"])
    r = await client.post(
        f"/api/v1/learning/tasks/{t['id']}/reveal",
        json={"idempotency_key": key()},
        headers=csrf(me),
    )
    body = r.json()
    assert body["verdict"] == "revealed" and body["expected"] == "ten" and body["task_done"]
    again = await answer(client, me, t, await correct_answer(t))
    assert again.status_code == 409
    assert (await progress_rows())["der"].error_count == 0


async def test_spelling_feedback(db, client):
    await seed_words(words=[("Haus", "NOUN", "dům")])
    me = await child_session(client)
    s = await start(client, me)
    t = await next_task(client, s["id"])
    r = (await answer(client, me, t, {"text": "haus"})).json()
    assert r["verdict"] == "case" and r["note"] == "de_noun_capital" and not r["correct"]
    r = (await answer(client, me, t, {"text": "das Haus"})).json()
    assert r["correct"]
    assert (await progress_rows())["Haus"].orthography_score is None  # measured in checks only


# ------------------------------------------------------------------ checking (Ověření)


async def test_check_first_try_correct_is_evidence_and_schedules(db, client, clock):
    await seed_words()
    me = await child_session(client)
    s = await checkable(client, me, clock)
    assert s["mode"] == "check" and s["total"] == 4 and s["words"] == [] and s["scene"] is None
    t = await next_task(client, s["id"])
    assert t["type"] == "recognition" and not t["is_new_item"]
    r = (await answer(client, me, t, await correct_answer(t))).json()
    assert r["counted"] and r["expected"] == "ten"
    p = (await progress_rows())["der"]
    assert p.correct_count == 1 and p.review_streak == 1
    assert p.next_review_at == clock.now + timedelta(days=1)
    assert p.last_error_free_at == clock.now and p.phonetic_score is None


async def test_check_wrong_answer_closes_the_task(db, client, clock):
    await seed_words()
    me = await child_session(client)
    s = await checkable(client, me, clock)
    t = await next_task(client, s["id"])
    r = (await answer(client, me, t, await wrong_answer(t))).json()
    assert not r["correct"] and r["task_done"] and not r["can_retry"] and r["expected"] == "ten"
    assert (await answer(client, me, t, await correct_answer(t))).status_code == 409
    p = (await progress_rows())["der"]
    assert p.error_count == 1 and p.review_streak == 0
    assert p.next_review_at > clock.now  # due again tomorrow, not in the same sitting


async def test_check_has_no_hints(db, client, clock):
    await seed_words()
    me = await child_session(client)
    s = await checkable(client, me, clock)
    t = await next_task(client, s["id"])
    h = await client.post(f"/api/v1/learning/tasks/{t['id']}/hint", headers=csrf(me))
    assert h.status_code == 409 and h.json()["detail"] == "hints_disabled"


async def test_check_dont_know_counts_as_error(db, client, clock):
    await seed_words()
    me = await child_session(client)
    s = await checkable(client, me, clock)
    t = await next_task(client, s["id"])
    r = await client.post(
        f"/api/v1/learning/tasks/{t['id']}/reveal",
        json={"idempotency_key": key()},
        headers=csrf(me),
    )
    assert r.json()["verdict"] == "revealed"
    assert (await progress_rows())["der"].error_count == 1


async def test_check_measures_spelling(db, client, clock):
    await seed_words(words=[("Haus", "NOUN", "dům")])
    me = await child_session(client)
    s = await checkable(client, me, clock)
    t = await next_task(client, s["id"])
    assert t["type"] == "recall"
    r = (await answer(client, me, t, {"text": "haus"})).json()
    assert r["verdict"] == "case" and r["task_done"]
    assert (await progress_rows())["Haus"].orthography_score == 0.6


async def test_lesson_and_check_can_be_open_together(db, client, clock):
    await seed_words()
    me = await child_session(client)
    c = await checkable(client, me, clock)
    lesson = await start(client, me)
    assert lesson["id"] != c["id"]
    prog = (await client.get("/api/v1/learning/progress")).json()
    assert prog["active_session_id"] == lesson["id"]
    assert prog["active_check_session_id"] == c["id"]


async def test_duplicate_submission_is_replayed(db, client, clock):
    await seed_words()
    me = await child_session(client)
    s = await checkable(client, me, clock)
    t = await next_task(client, s["id"])
    body = await wrong_answer(t)
    k = key()
    first = (await answer(client, me, t, body, k)).json()
    second = (await answer(client, me, t, body, k)).json()
    assert first == second and first["attempts"] == 1
    p = (await progress_rows())["der"]
    assert p.error_count == 1


async def test_concurrent_duplicate_submissions(db, client, clock):
    await seed_words()
    me = await child_session(client)
    s = await checkable(client, me, clock)
    t = await next_task(client, s["id"])
    body = await correct_answer(t)
    k = key()
    async with get_engine().connect() as conn:
        before = (await conn.execute(select(func.count()).select_from(LearningEvent))).scalar_one()
    results = await asyncio.gather(*(answer(client, me, t, body, k) for _ in range(5)))
    assert all(r.status_code == 200 for r in results)
    assert len({r.text for r in results}) == 1
    async with get_engine().connect() as conn:
        n = (await conn.execute(select(func.count()).select_from(LearningEvent))).scalar_one()
    assert n == before + 1
    assert (await progress_rows())["der"].correct_count == 1


async def test_concurrent_different_attempts_serialise(db, client, clock):
    await seed_words()
    me = await child_session(client)
    s = await checkable(client, me, clock)
    t = await next_task(client, s["id"])
    body = await correct_answer(t)
    results = await asyncio.gather(*(answer(client, me, t, body) for _ in range(3)))
    codes = sorted(r.status_code for r in results)
    assert codes == [200, 409, 409]  # first closes the task; the rest see it closed
    assert (await progress_rows())["der"].correct_count == 1


# ------------------------------------------------------------------ knowledge rules


async def test_passive_and_active_known_need_two_days(db, client, clock):
    await seed_words(words=[("Haus", "NOUN", "dům"), ("Hund", "NOUN", "pes")])
    me = await child_session(client)
    await run_lesson(client, me)
    clock.advance(days=1)
    await run_check(client, me)  # day 1: one recognition check per word
    p = (await progress_rows())["Haus"]
    assert p.correct_count == 1 and not p.passive_known
    while not (await progress_rows())["Haus"].active_known:
        clock.advance(days=31)  # past every interval, so the words are due
        assert await run_check(client, me) is not None
    p = (await progress_rows())["Haus"]
    assert p.passive_known and p.active_known and p.known_since_at is not None


async def test_mastered_after_delayed_check(db, client, clock):
    await seed_words(words=[("Haus", "NOUN", "dům"), ("Hund", "NOUN", "pes")])
    me = await child_session(client)
    await run_lesson(client, me)
    while not (await progress_rows())["Haus"].active_known:
        clock.advance(days=31)
        await run_check(client, me)
    p = (await progress_rows())["Haus"]
    assert p.state == ProgressState.LEARNING
    clock.advance(days=6)
    await svc_force_due()
    await run_check(client, me)
    assert (await progress_rows())["Haus"].state == ProgressState.LEARNING  # < 7 days
    clock.advance(days=2)
    await svc_force_due()
    await run_check(client, me)
    assert (await progress_rows())["Haus"].state == ProgressState.MASTERED


async def svc_force_due() -> None:
    async with get_engine().begin() as conn:
        await conn.execute(
            update(UserWordProgress).values(next_review_at=UserWordProgress.first_seen_at)
        )


async def test_languages_are_independent(db, client):
    await seed_words("de")
    await seed_words("fr")
    me = await child_session(client)
    await run_lesson(client, me, "de")
    fr = (await client.get("/api/v1/learning/progress?language=fr")).json()
    de = (await client.get("/api/v1/learning/progress?language=de")).json()
    assert fr["seen"] == 0 and de["seen"] == 4 and de["introduced"] == 4


async def test_grammar_unlock_persists(db, client, clock, monkeypatch):
    monkeypatch.setattr(svc, "GRAMMAR_GATE_WORDS", 2)
    await seed_words(words=[("Haus", "NOUN", "dům"), ("Hund", "NOUN", "pes")])
    me = await child_session(client)
    await run_lesson(client, me)
    for _ in range(8):
        clock.advance(days=31)
        await run_check(client, me)
    prog = (await client.get("/api/v1/learning/progress?language=de")).json()
    assert prog["known"] == 2 and prog["grammar_unlocked"]
    # Decay must not re-lock grammar.
    clock.advance(days=60)
    async for db_ in get_session():
        await svc.decay_sweep(db_, clock.now)
        await db_.commit()
    assert (await client.get("/api/v1/learning/progress?language=de")).json()["grammar_unlocked"]


# ------------------------------------------------------------------ decay


async def test_decay_boundary_and_idempotence(db, client, clock):
    await seed_words(words=[("Haus", "NOUN", "dům"), ("Hund", "NOUN", "pes")])
    me = await child_session(client)
    await run_lesson(client, me)
    clock.advance(days=1)
    await run_check(client, me)
    async with get_engine().begin() as conn:
        await conn.execute(
            update(UserWordProgress).values(
                state=ProgressState.MASTERED,
                orthography_score=0.9,
                next_review_at=clock.now + timedelta(days=90),
            )
        )
    async for db_ in get_session():
        assert await svc.decay_sweep(db_, clock.now + timedelta(days=30)) == 0  # boundary
        n = await svc.decay_sweep(db_, clock.now + timedelta(days=30, seconds=1))
        assert n == 2
        assert await svc.decay_sweep(db_, clock.now + timedelta(days=45)) == 0  # idempotent
        await db_.commit()
    p = (await progress_rows())["Haus"]
    assert p.state == ProgressState.LEARNING and p.review_streak == 0
    assert p.next_review_at <= clock.now + timedelta(days=31)  # back in priority review
    assert p.orthography_score == 0.9  # measurements are kept, not decayed
    assert p.last_decay_at == clock.now + timedelta(days=30, seconds=1)


# ------------------------------------------------------------------ isolation & import


async def test_other_profile_cannot_touch_lesson(db, client):
    await seed_words()
    parent = await setup_parent(client)
    await make_child(client, parent, "eva", "4321")
    await make_child(client, parent, "adam", "5678")
    eva = await login(client, "eva", "4321")
    s = await start(client, eva)
    t = await next_task(client, s["id"])
    adam = await login(client, "adam", "5678")
    assert (await client.get(f"/api/v1/learning/sessions/{s['id']}")).status_code == 404
    assert (await client.get(f"/api/v1/learning/sessions/{s['id']}/next")).status_code == 404
    r = await answer(client, adam, t, {"choice": 0})
    assert r.status_code == 404


async def test_parent_handover_learns_as_child(db, client):
    await seed_words()
    parent = await setup_parent(client)
    eva = await make_child(client, parent)
    switched = (
        await client.post(
            "/api/v1/auth/switch", json={"profile_id": eva["id"]}, headers=csrf(parent)
        )
    ).json()
    await run_lesson(client, switched)
    async for db_ in get_session():
        owners = (await db_.execute(select(UserWordProgress.user_id).distinct())).scalars().all()
    assert [str(o) for o in owners] == [eva["id"]]


async def test_reimport_keeps_progress(db, client):
    await seed_words()
    me = await child_session(client)
    await run_lesson(client, me)
    before = {k: (v.introduced_at, v.lexicon_item_id) for k, v in (await progress_rows()).items()}
    changed = [(w, pos, cs + " (upr.)") for w, pos, cs in WORDS["de"]]
    await seed_words(words=changed)
    after = {k: (v.introduced_at, v.lexicon_item_id) for k, v in (await progress_rows()).items()}
    assert before == after


async def test_progress_overview(db, client):
    await seed_words()
    me = await child_session(client)
    await run_lesson(client, me)
    p = (await client.get("/api/v1/learning/progress")).json()
    assert p["language"] == "de" and p["lexicon_items"] == 6 and p["seen"] == 4
    assert p["by_state"]["LEARNING"] == 4 and p["known"] == 0
    assert p["introduced"] == 4 and p["due_now"] == 0  # checkable from tomorrow
    assert p["next_milestone"] == 100 and p["grammar_gate"] == 1000
    assert p["phonetic_measured"] == 0 and p["active_session_id"] is None
    assert p["active_check_session_id"] is None
    assert p["by_band"] == [{"band": 100, "items": 6, "known": 0}]


async def test_recall_shows_cloze_for_ambiguous_words(db, client):
    from app.cli import LexiconRow, upsert_lexicon

    await upsert_lexicon(
        [
            LexiconRow(
                language="de",
                rank=1,
                lemma="der",
                pos="DET",
                translation_cs="ten (určitý člen)",
                example="Der Hund schläft.",
            )
        ]
    )
    me = await child_session(client)
    s = await start(client, me)
    t = await next_task(client, s["id"])
    assert t["type"] == "recall" and t["cloze"] == "___ Hund schläft." and t["example"] is None
    r = (await answer(client, me, t, {"text": "der"})).json()
    assert r["correct"]
