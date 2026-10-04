"""Placement test (rozřazovací test): where a learner who already knows some words starts.

Graded like a check (one attempt, no hints, "Nevím" instead of guessing) but adaptive: each
answer picks the next word (`app.domain.placement`). Callers own the transaction.

- A first-try correct answer is one piece of check evidence for that word, which then skips
  its lesson. A miss is exposure only: the word stays for the lessons.
- Finishing sets the level. Words up to it that the test did not ask skip the lessons and wait
  in Ověření to be confirmed; nothing is marked known by assumption. A check that misses one
  sends it back to the lessons (`learning._apply_progress`).
- Lessons then continue with the words above the level, since they pick words not introduced.
"""

import random
from datetime import datetime

from sqlalchemy import DateTime, and_, func, literal, or_, select, true, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Language
from app.domain.learning_policy import POLICY
from app.domain.placement import PLACEMENT, estimate, next_rank
from app.models import (
    LanguagePlacement,
    LearningSession,
    LearningTask,
    LexiconItem,
    User,
    UserWordProgress,
)
from app.models.learning import TaskStatus, TaskType
from app.services import learning as lsvc

PLACED, SKIPPED = "placed", "skipped"
NEAREST = 3  # pick among this many closest words, so a retake does not repeat itself


async def ceiling(db: AsyncSession, user: User, language: Language) -> int:
    """Highest rank the test can ask (the lexicon holds no higher words for this profile)."""
    return (
        await db.scalar(
            select(func.coalesce(func.max(LexiconItem.frequency_rank), 0)).where(
                LexiconItem.language == language, lsvc._suitable(user)
            )
        )
    ) or 0


async def get_placement(
    db: AsyncSession, user: User, language: Language
) -> LanguagePlacement | None:
    return await db.get(LanguagePlacement, (user.id, language))


async def skip(db: AsyncSession, user: User, language: Language, now: datetime) -> None:
    """Start from the beginning: stop offering the test. Keeps an earlier test's level."""
    await db.execute(
        pg_insert(LanguagePlacement)
        .values(user_id=user.id, language=language, status=SKIPPED, decided_at=now)
        .on_conflict_do_nothing()
    )


def _answers(session: LearningSession) -> list[tuple[int, bool]]:
    return [
        (t.item.frequency_rank, bool(t.first_try_correct))
        for t in session.tasks
        if t.status != TaskStatus.PENDING
    ]


async def add_next_task(
    db: AsyncSession, user: User, session: LearningSession, rng: random.Random
) -> LearningTask | None:
    """Append the next question, or None when the test has enough answers (or no words)."""
    top = await ceiling(db, user, session.language)
    rank = next_rank(_answers(session), top)
    if rank is None:
        return None
    asked = [t.lexicon_item_id for t in session.tasks]
    on, still_new = lsvc._not_introduced(user)
    nearest = list(
        (
            await db.execute(
                select(LexiconItem)
                .outerjoin(UserWordProgress, on)
                .where(
                    LexiconItem.language == session.language,
                    # Words not taught yet, including those an earlier test queued (a retake).
                    or_(still_new, _queued_unchecked()),
                    lsvc._suitable(user),
                    LexiconItem.id.not_in(asked) if asked else true(),
                )
                .order_by(func.abs(LexiconItem.frequency_rank - rank), LexiconItem.frequency_rank)
                .limit(NEAREST)
            )
        ).scalars()
    )
    if not nearest:
        return None
    item = rng.choice(nearest)
    payload = await lsvc._recognition_payload(db, user, item, rng)
    if payload is None:
        return None  # a one-word lexicon: nothing to choose from
    task = LearningTask(
        session_id=session.id,
        lexicon_item_id=item.id,
        position=len(session.tasks),
        task_type=TaskType.RECOGNITION,
        is_new_item=False,
        payload=payload,
    )
    db.add(task)
    await db.flush()
    return task


async def record_answer(
    db: AsyncSession, user: User, item: LexiconItem, *, evidence: bool, now: datetime
) -> None:
    """A correct first try is check evidence and skips the word's lesson; a miss is exposure."""
    if not evidence:
        await lsvc.mark_seen(db, user, item, now)
        return
    await lsvc._apply_progress(
        db,
        user,
        item,
        TaskType.RECOGNITION,
        now=now,
        first_attempt=True,
        evidence=True,
        orthography=None,
    )
    await db.execute(
        update(UserWordProgress)
        .where(
            UserWordProgress.user_id == user.id,
            UserWordProgress.lexicon_item_id == item.id,
            UserWordProgress.introduced_at.is_(None),
        )
        .values(introduced_at=now, introduced_by="placement")
    )


async def finish(db: AsyncSession, user: User, session: LearningSession, now: datetime) -> dict:
    """Place the learner from the answers given; returns the summary fields of the result."""
    answers = _answers(session)
    top = await ceiling(db, user, session.language)
    est = estimate(answers, top)
    summary: dict = {"placed": est is not None, "ceiling": top, "asked": len(answers)}
    if est is None:
        return summary  # stopped too early to say: nothing changes

    values = {
        "status": PLACED,
        "level": est.level,
        "level_low": est.low,
        "level_high": est.high,
        "ceiling": top,
        "session_id": session.id,
        "decided_at": now,
        "policy_version": PLACEMENT.version,
    }
    await db.execute(
        pg_insert(LanguagePlacement)
        .values(user_id=user.id, language=session.language, **values)
        .on_conflict_do_update(index_elements=["user_id", "language"], set_=values)
    )

    p, li = UserWordProgress, LexiconItem
    missed = [t.lexicon_item_id for t in session.tasks if t.first_try_correct is False]
    # A retake: words an earlier test queued, that no check has asked yet, go back to the
    # lessons when they now lie above the level or this test missed them.
    above = select(li.id).where(li.language == session.language, li.frequency_rank > est.level)
    await db.execute(
        update(p)
        .where(
            p.user_id == user.id,
            _queued_unchecked(),
            or_(p.lexicon_item_id.in_(above), p.lexicon_item_id.in_(missed)),
        )
        .values(introduced_at=None, introduced_by=None, next_review_at=None)
    )
    # Words up to the level that the test did not ask (or asked and the learner knew) skip
    # the lessons and are checkable now. Words missed in the test stay for the lessons.
    candidates = select(
        func.gen_random_uuid(),
        literal(user.id),
        li.id,
        literal(now, DateTime(timezone=True)),
        literal("placement"),
        literal(now, DateTime(timezone=True)),
        literal(POLICY.version),
    ).where(
        li.language == session.language,
        li.frequency_rank <= est.level,
        lsvc._suitable(user),
        li.id.not_in(missed) if missed else true(),
    )
    stmt = pg_insert(p).from_select(
        [
            "id",
            "user_id",
            "lexicon_item_id",
            "introduced_at",
            "introduced_by",
            "next_review_at",
            "policy_version",
        ],
        candidates,
    )
    queued = await db.execute(
        stmt.on_conflict_do_update(
            constraint="uq_user_word_progress_user_item",
            set_={
                "introduced_at": now,
                "introduced_by": "placement",
                "next_review_at": now,
            },
            where=p.introduced_at.is_(None),
        )
    )
    summary.update(
        level=est.level,
        level_low=est.low,
        level_high=est.high,
        at_ceiling=est.at_ceiling,
        queued=queued.rowcount or 0,
    )
    return summary


def _queued_unchecked():
    """Queued by a placement test and not asked by any check (nor answered right in a test)."""
    p = UserWordProgress
    return and_(p.introduced_by == "placement", p.last_reviewed_at.is_(None))


def is_unconfirmed_placement():
    """Check ordering: words a placement queued and no check has confirmed come last."""
    p = UserWordProgress
    return and_(p.introduced_by == "placement", p.correct_count == 0)
