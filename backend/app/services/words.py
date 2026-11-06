"""My dictionary (Můj slovník): the words a profile has met, with their state and history.

Only words with a progress row (seen in a lesson, a test or a check) are listed: the dictionary
is the learner's own, not a way around the lessons. The content filter applies as everywhere.
"""

import uuid
from datetime import datetime

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Language, ProgressState
from app.models import LearningEvent, LexiconItem, User, UserWordProgress
from app.services.learning import LearningError, _suitable

STATUSES = ("mastered", "known", "passive", "learning", "seen")


def _status():
    p = UserWordProgress
    return case(
        (p.state == ProgressState.MASTERED, "mastered"),
        (and_(p.passive_known.is_(True), p.active_known.is_(True)), "known"),
        (p.passive_known.is_(True), "passive"),
        (p.introduced_at.is_not(None), "learning"),
        else_="seen",
    )


def _escape(q: str) -> str:
    return q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def list_words(
    db: AsyncSession,
    user: User,
    language: Language,
    now: datetime,
    *,
    q: str | None,
    status: str | None,
    due: bool,
    offset: int,
    limit: int,
) -> dict:
    p, li = UserWordProgress, LexiconItem
    st = _status().label("status")
    base = (
        select(li, p, st)
        .join(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
        .where(li.language == language, _suitable(user))
    )
    counts = dict(
        (
            await db.execute(
                select(st, func.count())
                .select_from(li)
                .join(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
                .where(li.language == language, _suitable(user))
                .group_by(st)
            )
        ).all()
    )
    if q and q.strip():
        pat = f"%{_escape(q.strip().lower())}%"
        base = base.where(
            or_(
                func.lower(li.lemma).like(pat, escape="\\"),
                func.lower(li.translation_cs).like(pat, escape="\\"),
            )
        )
    if status in STATUSES:
        base = base.where(_status() == status)
    if due:
        base = base.where(p.introduced_at.is_not(None), p.next_review_at <= now)
    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    rows = (await db.execute(base.order_by(li.frequency_rank).offset(offset).limit(limit))).all()
    return {
        "total": total or 0,
        "counts": {s: counts.get(s, 0) for s in STATUSES},
        "items": [
            {
                "id": item.id,
                "lemma": item.lemma,
                "gender": item.gender,
                "pos": item.pos,
                "rank": item.frequency_rank,
                "translation": item.translation_cs,
                "status": status_,
                "due": prog.introduced_at is not None
                and prog.next_review_at is not None
                and prog.next_review_at <= now,
                "next_review_at": prog.next_review_at,
                "correct": prog.correct_count,
                "errors": prog.error_count,
            }
            for item, prog, status_ in rows
        ],
    }


async def word_detail(db: AsyncSession, user: User, item_id: uuid.UUID, now: datetime) -> dict:
    p, li = UserWordProgress, LexiconItem
    row = (
        await db.execute(
            select(li, p, _status())
            .join(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
            .where(li.id == item_id, _suitable(user))
        )
    ).one_or_none()
    if row is None:
        raise LearningError("word_not_found", 404)
    item, prog, status = row
    ev = LearningEvent
    history = (
        await db.execute(
            select(ev)
            .where(ev.user_id == user.id, ev.lexicon_item_id == item_id)
            .order_by(ev.occurred_at.desc())
            .limit(20)
        )
    ).scalars()
    return {
        "id": item.id,
        "language": item.language,
        "lemma": item.lemma,
        "gender": item.gender,
        "pos": item.pos,
        "rank": item.frequency_rank,
        "translation": item.translation_cs,
        "ipa": item.ipa,
        "example": item.example_sentence,
        "review_status": item.source or None,
        "status": status,
        "passive_known": prog.passive_known,
        "active_known": prog.active_known,
        "correct": prog.correct_count,
        "errors": prog.error_count,
        "introduced_at": prog.introduced_at,
        "introduced_by": prog.introduced_by,
        "last_reviewed_at": prog.last_reviewed_at,
        "next_review_at": prog.next_review_at,
        "review_streak": prog.review_streak,
        "history": [
            {
                "at": e.occurred_at,
                "correct": e.is_correct,
                "graded": e.counts_as_evidence,
                "task": e.task_type.value,
                "mode": e.answer_mode,
                "error_tag": e.error_tag,
            }
            for e in history
        ],
    }


async def audio_text(
    db: AsyncSession, user: User, item_id: uuid.UUID, part: str
) -> tuple[Language, str]:
    p, li = UserWordProgress, LexiconItem
    item = (
        await db.execute(
            select(li)
            .join(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
            .where(li.id == item_id, _suitable(user))
        )
    ).scalar_one_or_none()
    if item is None:
        raise LearningError("word_not_found", 404)
    text = item.lemma if part == "word" else item.example_sentence
    if not text:
        raise LearningError("no_example", 404)
    if part == "word" and item.gender and item.language == Language.DE:
        text = f"{item.gender} {item.lemma}"
    return item.language, text
