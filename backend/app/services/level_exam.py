"""Vocabulary level exams (zkouška úrovně slovní zásoby): A1, A2, B1, B2 per language.

Rules live in `app.domain.level_exam`. Callers own the transaction.

- An exam opens per language and level once the band is imported, the previous level is
  earned, and enough of the band is known (or a placement test reached past it). A failed exam
  can be retaken from the next local day, on a fresh sample.
- Each answer is graded like Ověření: a first-try correct answer is check evidence, a miss
  schedules the word as a check miss would (a word no lesson taught yet stays for the lessons).
- Passing records a LevelBadge. The result lists the words missed, to practise.
"""

import random
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func, literal, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.diagnostic import band_at_most
from app.domain.enums import CefrLevel, Language, ProgressState
from app.domain.level_exam import (
    BY_LEVEL,
    EXAM,
    LEVELS,
    ExamLevel,
    band_complete,
    passed,
    prerequisite_rank_ceiling,
    previous,
    ready,
)
from app.models import (
    CefrPlacement,
    GrammarUnit,
    LearningSession,
    LearningTask,
    LevelBadge,
    LexiconItem,
    User,
    UserGrammarProgress,
    UserWordProgress,
)
from app.models.learning import SessionMode, SessionStatus, TaskStatus
from app.services import learning as lsvc
from app.services import placement


@dataclass(slots=True)
class LevelStatus:
    level: CefrLevel
    low: int
    high: int
    # earned | in_progress | missing_words | needs_previous | not_ready | retry_later | available
    state: str
    lexicon_items: int  # words of the band the app holds
    pool: int  # of those, the ones this profile can be asked (age filter)
    known: int  # passively known
    earned_at: datetime | None = None
    retry_from: datetime | None = None
    active_session_id: uuid.UUID | None = None
    last_correct: int | None = None
    last_asked: int | None = None


def _in_band(exam: ExamLevel):
    return and_(LexiconItem.frequency_rank > exam.low, LexiconItem.frequency_rank <= exam.high)


async def badges(db: AsyncSession, user: User, language: Language) -> list[LevelBadge]:
    return list(
        (
            await db.execute(
                select(LevelBadge)
                .where(LevelBadge.user_id == user.id, LevelBadge.language == language)
                .order_by(LevelBadge.level)
            )
        ).scalars()
    )


async def _last_attempt(
    db: AsyncSession, user: User, language: Language, level: CefrLevel
) -> LearningSession | None:
    return (
        await db.execute(
            select(LearningSession)
            .where(
                LearningSession.user_id == user.id,
                LearningSession.language == language,
                LearningSession.mode == SessionMode.EXAM,
                LearningSession.exam_level == level,
                LearningSession.status == SessionStatus.COMPLETED,
            )
            .order_by(LearningSession.completed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


def _retry_from(user: User, completed_at: datetime) -> datetime:
    """A failed exam can be retaken from the next local day after it."""
    return lsvc.next_local_midnight(user, completed_at)


async def statuses(
    db: AsyncSession, user: User, language: Language, now: datetime
) -> list[LevelStatus]:
    li, p = LexiconItem, UserWordProgress
    earned = {b.level: b for b in await badges(db, user, language)}
    active = await lsvc.get_active_session(db, user, language, SessionMode.EXAM)
    placed = await placement.get_placement(db, user, language)
    placement_level = placed.level if placed and placed.status == placement.PLACED else None
    cefr = await db.get(CefrPlacement, (user.id, language))
    cefr_level = cefr.level if cefr is not None else None

    out: list[LevelStatus] = []
    for exam in LEVELS:
        lexicon_items, pool, known = (
            await db.execute(
                select(
                    func.count(li.id),
                    func.count(li.id).filter(lsvc._suitable(user)),
                    func.count(li.id).filter(lsvc._suitable(user), p.passive_known.is_(True)),
                )
                .outerjoin(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
                .where(li.language == language, _in_band(exam))
            )
        ).one()
        st = LevelStatus(exam.level, exam.low, exam.high, "", lexicon_items, pool, known)
        last = await _last_attempt(db, user, language, exam.level)
        if last is not None:
            st.last_correct = last.summary.get("correct")
            st.last_asked = last.summary.get("asked")
        prev = previous(exam.level)
        if exam.level in earned:
            st.state, st.earned_at = "earned", earned[exam.level].earned_at
        elif active is not None and active.exam_level == exam.level:
            st.state, st.active_session_id = "in_progress", active.id
        elif not band_complete(exam, lexicon_items) or pool < EXAM.questions:
            st.state = "missing_words"
        elif prev is not None and prev not in earned:
            st.state = "needs_previous"
        elif not ready(
            exam, pool, known, placement_level, cefr_reached=band_at_most(exam.level, cefr_level)
        ):
            st.state = "not_ready"
        elif last is not None and now < (retry := _retry_from(user, last.completed_at)):
            st.state, st.retry_from = "retry_later", retry
        else:
            st.state = "available"
        out.append(st)
    return out


async def plan(
    db: AsyncSession,
    user: User,
    language: Language,
    level: CefrLevel,
    now: datetime,
    rng: random.Random,
) -> list[LexiconItem]:
    """The exam's words, or LearningError when it cannot be taken now."""
    if level not in BY_LEVEL:
        raise lsvc.LearningError("exam_level_invalid", 422)
    status = next(s for s in await statuses(db, user, language, now) if s.level == level)
    if status.state != "available":
        raise lsvc.LearningError(f"exam_{status.state}")
    exam = BY_LEVEL[level]
    # Fresh sample: words earlier attempts at this level asked come last.
    asked_before = (
        select(LearningTask.lexicon_item_id)
        .join(LearningSession, LearningSession.id == LearningTask.session_id)
        .where(
            LearningSession.user_id == user.id,
            LearningSession.mode == SessionMode.EXAM,
            LearningSession.exam_level == level,
        )
        .scalar_subquery()
    )
    rows = (
        await db.execute(
            select(LexiconItem, LexiconItem.id.in_(asked_before)).where(
                LexiconItem.language == language, _in_band(exam), lsvc._suitable(user)
            )
        )
    ).all()
    fresh = [item for item, seen in rows if not seen]
    used = [item for item, seen in rows if seen]
    rng.shuffle(fresh)
    rng.shuffle(used)
    return (fresh + used)[: EXAM.questions]


async def record_answer(
    db: AsyncSession, user: User, item: LexiconItem, *, evidence: bool, now: datetime
) -> None:
    """Graded exactly like a placement answer, which is graded like a check."""
    await placement.record_answer(db, user, item, evidence=evidence, now=now)


async def finish(db: AsyncSession, user: User, session: LearningSession, now: datetime) -> dict:
    """Score the exam; a pass records the badge. Unanswered questions count as missed."""
    tasks = session.tasks
    answered = sum(t.status != TaskStatus.PENDING for t in tasks)
    correct = sum(bool(t.first_try_correct) for t in tasks)
    ok = len(tasks) >= EXAM.questions and passed(correct, answered)
    summary: dict = {
        "exam_level": session.exam_level.value if session.exam_level else None,
        "passed": ok,
        "correct": correct,
        "asked": len(tasks),
        "answered": answered,
        "pass_correct": EXAM.pass_correct,
        "policy_version": EXAM.version,
        "missed": [
            {"lemma": t.item.lemma, "gender": t.item.gender, "translation": t.item.translation_cs}
            for t in tasks
            if not t.first_try_correct
        ],
    }
    if ok:
        await db.execute(
            pg_insert(LevelBadge)
            .values(
                user_id=user.id,
                language=session.language,
                level=session.exam_level,
                earned_at=now,
                session_id=session.id,
                correct=correct,
                asked=len(tasks),
                policy_version=EXAM.version,
            )
            .on_conflict_do_nothing()
        )
        # The passed exam supplies aggregate level evidence. Preserve answer counters/events;
        # this unlocks and completes prerequisite pools without fabricating per-item attempts.
        ceiling = prerequisite_rank_ceiling(session.exam_level)
        eligible_words = select(LexiconItem.id).where(
            LexiconItem.language == session.language,
            LexiconItem.frequency_rank <= ceiling,
            lsvc._suitable(user),
        )
        await db.execute(
            update(UserWordProgress)
            .where(
                UserWordProgress.user_id == user.id,
                UserWordProgress.lexicon_item_id.in_(eligible_words),
            )
            .values(
                state=ProgressState.MASTERED,
                passive_known=True,
                active_known=True,
                introduced_at=func.coalesce(UserWordProgress.introduced_at, now),
                introduced_by=func.coalesce(UserWordProgress.introduced_by, "placement"),
                next_review_at=func.coalesce(UserWordProgress.next_review_at, now),
                known_since_at=func.coalesce(UserWordProgress.known_since_at, now),
            )
        )
        await db.execute(
            pg_insert(UserWordProgress)
            .from_select(
                [
                    "id",
                    "user_id",
                    "lexicon_item_id",
                    "state",
                    "passive_known",
                    "active_known",
                    "introduced_at",
                    "introduced_by",
                    "next_review_at",
                    "known_since_at",
                ],
                select(
                    func.gen_random_uuid(),
                    literal(user.id),
                    LexiconItem.id,
                    literal(ProgressState.MASTERED.value, type_=UserWordProgress.state.type),
                    literal(True),
                    literal(True),
                    literal(now),
                    literal("placement"),
                    literal(now),
                    literal(now),
                ).where(
                    LexiconItem.language == session.language,
                    LexiconItem.frequency_rank <= ceiling,
                    lsvc._suitable(user),
                ),
            )
            .on_conflict_do_nothing(constraint="uq_user_word_progress_user_item")
        )
        eligible_units = select(GrammarUnit.id).where(
            GrammarUnit.language == session.language,
            GrammarUnit.level <= session.exam_level,
            GrammarUnit.active.is_(True),
        )
        await db.execute(
            update(UserGrammarProgress)
            .where(
                UserGrammarProgress.user_id == user.id,
                UserGrammarProgress.unit_id.in_(eligible_units),
            )
            .values(
                state=ProgressState.MASTERED,
                studied_at=func.coalesce(UserGrammarProgress.studied_at, now),
                studied_by=func.coalesce(UserGrammarProgress.studied_by, "placement"),
                next_review_at=func.coalesce(UserGrammarProgress.next_review_at, now),
                known_since_at=func.coalesce(UserGrammarProgress.known_since_at, now),
            )
        )
        await db.execute(
            pg_insert(UserGrammarProgress)
            .from_select(
                [
                    "user_id",
                    "unit_id",
                    "state",
                    "studied_at",
                    "studied_by",
                    "next_review_at",
                    "known_since_at",
                ],
                select(
                    literal(user.id),
                    GrammarUnit.id,
                    literal(ProgressState.MASTERED.value, type_=UserGrammarProgress.state.type),
                    literal(now),
                    literal("placement"),
                    literal(now),
                    literal(now),
                ).where(
                    GrammarUnit.language == session.language,
                    GrammarUnit.level <= session.exam_level,
                    GrammarUnit.active.is_(True),
                ),
            )
            .on_conflict_do_nothing()
        )
    else:
        summary["retry_from"] = _retry_from(user, now).isoformat()
    return summary
