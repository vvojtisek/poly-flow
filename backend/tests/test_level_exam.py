"""Vocabulary level exams: the rules (pure) and the flow through the API."""

from datetime import datetime

from sqlalchemy import select, update

from app.cli import LexiconRow, upsert_lexicon
from app.db.session import get_session
from app.domain.enums import CefrLevel
from app.domain.level_exam import EXAM, LEVELS, band_complete, passed, previous, ready
from app.models import LanguagePlacement, LearningEvent, LevelBadge, LexiconItem, User
from app.models import UserWordProgress as P
from tests.helpers import csrf, login, make_child, setup_parent
from tests.test_learning import key, next_task, overrides  # noqa: F401  (fixture)

# ---------------------------------------------------------------- domain


def test_levels_follow_the_milestone_tags():
    assert [(e.level, e.low, e.high) for e in LEVELS] == [
        (CefrLevel.A1, 0, 500),
        (CefrLevel.A2, 500, 1000),
        (CefrLevel.B1, 1000, 2500),
        (CefrLevel.B2, 2500, 5000),
    ]
    assert previous(CefrLevel.A1) is None and previous(CefrLevel.B2) is CefrLevel.B1


def test_pass_mark_needs_every_question_answered():
    assert passed(26, 30) and passed(30, 30)
    assert not passed(25, 30)
    assert not passed(26, 29)  # stopped early


def test_band_must_be_imported_and_mostly_known():
    a1 = LEVELS[0]
    assert not band_complete(a1, 100)  # today's core-100 cannot stand for 500 words
    assert band_complete(a1, 450) and not band_complete(a1, 449)
    assert not ready(a1, pool=500, known=399, placement_level=None)
    assert ready(a1, pool=500, known=400, placement_level=None)
    assert ready(a1, pool=500, known=0, placement_level=500)  # placed past the band
    assert not ready(a1, pool=500, known=0, placement_level=499)


# ---------------------------------------------------------------- API

N_WORDS = 1100  # A1 and A2 bands complete, B1 not


async def seed(n: int = N_WORDS, flagged: frozenset[int] = frozenset()) -> None:
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


async def know(username: str, up_to: int, now: datetime) -> None:
    """Mark the first `up_to` words passively known, as checks over several days would."""
    async for db in get_session():
        user = (await db.execute(select(User).where(User.username == username))).scalar_one()
        items = (
            await db.execute(select(LexiconItem.id).where(LexiconItem.frequency_rank <= up_to))
        ).scalars()
        for item_id in items:
            db.add(
                P(
                    user_id=user.id,
                    lexicon_item_id=item_id,
                    passive_known=True,
                    correct_count=3,
                    introduced_at=now,
                    introduced_by="lesson",
                    next_review_at=now,
                )
            )
        await db.commit()


async def levels(client) -> dict[str, dict]:
    r = await client.get("/api/v1/learning/levels?language=de")
    assert r.status_code == 200, r.text
    return {lv["level"]: lv for lv in r.json()["levels"]}


async def start_exam(client, me, level: str):
    return await client.post(
        "/api/v1/learning/sessions",
        json={"language": "de", "mode": "exam", "level": level},
        headers=csrf(me),
    )


def rank_of(task: dict) -> int:
    return int(task["prompt"].removeprefix("wort"))


async def take_exam(client, me, level: str, *, miss: int = 0) -> tuple[dict, list[int]]:
    """Answer every question, missing ("Nevím") the first `miss`; returns result and ranks."""
    r = await start_exam(client, me, level)
    assert r.status_code == 200, r.text
    s = r.json()["session"]
    assert s["mode"] == "exam" and s["total"] == EXAM.questions
    ranks = []
    while (t := await next_task(client, s["id"])) is not None:
        assert t["type"] == "recognition"
        rank = rank_of(t)
        ranks.append(rank)
        if len(ranks) <= miss:
            r = await client.post(
                f"/api/v1/learning/tasks/{t['id']}/reveal",
                json={"idempotency_key": key()},
                headers=csrf(me),
            )
        else:
            choice = next(o["id"] for o in t["options"] if o["text"] == f"význam {rank}")
            r = await client.post(
                f"/api/v1/learning/tasks/{t['id']}/answer",
                json={"idempotency_key": key(), "choice": choice},
                headers=csrf(me),
            )
        assert r.status_code == 200, r.text
    r = await client.post(f"/api/v1/learning/sessions/{s['id']}/complete", headers=csrf(me))
    assert r.status_code == 200, r.text
    return r.json()["summary"], ranks


async def test_core_100_cannot_stand_for_any_level(db, client):
    await seed(100)
    await setup_parent(client)
    lv = await levels(client)
    assert [v["state"] for v in lv.values()] == ["missing_words"] * 4
    assert lv["A1"]["lexicon_items"] == 100 and lv["A1"]["high"] == 500


async def test_exam_opens_once_the_band_is_mostly_known(db, client, overrides):  # noqa: F811
    await seed()
    me = await setup_parent(client)
    lv = await levels(client)
    assert lv["A1"]["state"] == "not_ready" and lv["A1"]["ready_known"] == 400
    assert lv["A2"]["state"] == "needs_previous"
    assert lv["B1"]["state"] == "missing_words"
    r = await start_exam(client, me, "A1")
    assert r.status_code == 409 and r.json()["detail"] == "exam_not_ready"
    r = await start_exam(client, me, "A2")
    assert r.status_code == 409 and r.json()["detail"] == "exam_needs_previous"

    await know("mama", 400, overrides.now)
    assert (await levels(client))["A1"]["state"] == "available"


async def test_placement_past_the_band_opens_the_exam(db, client, overrides):  # noqa: F811
    await seed()
    me = await setup_parent(client)
    async for s in get_session():
        user = (await s.execute(select(User))).scalar_one()
        s.add(
            LanguagePlacement(
                user_id=user.id,
                language="de",
                status="placed",
                level=600,
                level_low=500,
                level_high=700,
                ceiling=N_WORDS,
                decided_at=overrides.now,
            )
        )
        await s.commit()
    assert (await levels(client))["A1"]["state"] == "available"
    assert me


async def test_passing_records_a_badge_and_counts_as_checks(db, client, overrides):  # noqa: F811
    await seed()
    me = await setup_parent(client)
    await know("mama", 450, overrides.now)
    summary, ranks = await take_exam(client, me, "A1", miss=EXAM.questions - EXAM.pass_correct)
    assert all(1 <= r <= 500 for r in ranks) and len(set(ranks)) == EXAM.questions
    assert summary["passed"] and summary["correct"] == EXAM.pass_correct
    assert summary["exam_level"] == "A1" and len(summary["missed"]) == 4

    lv = await levels(client)
    assert lv["A1"]["state"] == "earned" and lv["A2"]["state"] == "not_ready"
    progress = (await client.get("/api/v1/learning/progress?language=de")).json()
    assert [b["level"] for b in progress["level_badges"]] == ["A1"]
    assert progress["level_badges"][0]["correct"] == EXAM.pass_correct

    async for s in get_session():
        events = (await s.execute(select(LearningEvent))).scalars().all()
        assert sum(e.counts_as_evidence for e in events) == EXAM.pass_correct
        badge = (await s.execute(select(LevelBadge))).scalar_one()
        assert badge.asked == EXAM.questions and badge.policy_version == EXAM.version

    r = await start_exam(client, me, "A1")
    assert r.status_code == 409 and r.json()["detail"] == "exam_earned"


async def test_failing_lists_words_and_allows_a_fresh_retake_tomorrow(db, client, overrides):  # noqa: F811
    await seed()
    me = await setup_parent(client)
    await know("mama", 500, overrides.now)
    summary, first = await take_exam(client, me, "A1", miss=5)
    assert not summary["passed"] and summary["correct"] == 25
    assert sorted(m["lemma"] for m in summary["missed"]) == sorted(f"wort{r}" for r in first[:5])

    # A missed known word is due again in Ověření tomorrow, like a check miss.
    async for s in get_session():
        missed = (
            await s.execute(
                select(P)
                .join(LexiconItem, LexiconItem.id == P.lexicon_item_id)
                .where(LexiconItem.frequency_rank.in_(first[:5]))
            )
        ).scalars()
        for p in missed:
            assert p.review_streak == 0 and p.next_review_at > overrides.now

    lv = await levels(client)
    assert lv["A1"]["state"] == "retry_later" and lv["A1"]["last_correct"] == 25
    r = await start_exam(client, me, "A1")
    assert r.status_code == 409 and r.json()["detail"] == "exam_retry_later"
    assert (await client.get("/api/v1/learning/progress?language=de")).json()["level_badges"] == []

    overrides.advance(days=1)
    assert (await levels(client))["A1"]["state"] == "available"
    summary, second = await take_exam(client, me, "A1")
    assert summary["passed"]
    assert not set(first) & set(second)  # a fresh sample while unasked words remain


async def test_unfinished_exam_resumes_and_does_not_pass(db, client, overrides):  # noqa: F811
    await seed()
    me = await setup_parent(client)
    await know("mama", 500, overrides.now)
    sid = (await start_exam(client, me, "A1")).json()["session"]["id"]
    assert (await levels(client))["A1"]["state"] == "in_progress"
    again = (await start_exam(client, me, "A1")).json()["session"]
    assert again["id"] == sid  # resumed, not re-sampled
    t = await next_task(client, sid)
    r = await client.post(f"/api/v1/learning/tasks/{t['id']}/hint", headers=csrf(me))
    assert r.status_code == 409 and r.json()["detail"] == "hints_disabled"

    r = await client.post(f"/api/v1/learning/sessions/{sid}/complete", headers=csrf(me))
    summary = r.json()["summary"]
    assert not summary["passed"] and summary["answered"] == 0
    assert len(summary["missed"]) == EXAM.questions


async def test_exam_needs_a_level(db, client):
    await seed(100)
    me = await setup_parent(client)
    r = await client.post(
        "/api/v1/learning/sessions", json={"language": "de", "mode": "exam"}, headers=csrf(me)
    )
    assert r.status_code == 422 and r.json()["detail"] == "exam_level_required"


async def test_child_is_never_asked_flagged_words(db, client, overrides):  # noqa: F811
    flagged = frozenset(range(3, 501, 7))
    await seed(flagged=flagged)
    parent = await setup_parent(client)
    await make_child(client, parent)
    child = await login(client, "eva", "4321")
    await know("eva", 500, overrides.now)
    lv = await levels(client)
    assert lv["A1"]["pool"] == 500 - len(flagged) and lv["A1"]["state"] == "available"
    summary, ranks = await take_exam(client, child, "A1")
    assert summary["passed"] and not set(ranks) & flagged


async def test_badge_survives_decay(db, client, overrides):  # noqa: F811
    await seed()
    me = await setup_parent(client)
    await know("mama", 500, overrides.now)
    await take_exam(client, me, "A1")
    async for s in get_session():
        await s.execute(update(P).values(passive_known=False))
        await s.commit()
    assert (await levels(client))["A1"]["state"] == "earned"
