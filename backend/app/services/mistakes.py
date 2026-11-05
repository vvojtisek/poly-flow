"""Mistake engine overview: what a profile gets wrong lately, across words and grammar.

Read-only aggregation over the graded logs (`learning_events` of checks and exams,
`grammar_attempts` of grammar checks). Lesson practice is excluded: mistakes there are part of
learning and say nothing about what the learner knows.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Language
from app.domain.learning_policy import POLICY
from app.models import (
    GrammarAttempt,
    GrammarUnit,
    LearningEvent,
    LearningSession,
    LexiconItem,
    User,
)
from app.models.learning import SessionMode
from app.services.learning import _suitable, recently_missed_words


@dataclass(slots=True)
class WeakWord:
    item: LexiconItem
    errors: int
    last_error_at: datetime
    tags: list[str]


@dataclass(slots=True)
class WeakUnit:
    unit: GrammarUnit
    errors: int
    last_error_at: datetime
    tags: list[str]


@dataclass(slots=True)
class WeakSpots:
    words: list[WeakWord]
    units: list[WeakUnit]
    tags: list[tuple[str, int]]
    window_days: int


async def weak_spots(
    db: AsyncSession, user: User, language: Language, now: datetime, limit: int = 10
) -> WeakSpots:
    since = now - POLICY.remediation_window
    ev = LearningEvent
    # Words still weak: their latest graded answer was wrong.
    items = await recently_missed_words(db, user, language, now, limit=limit)
    words: list[WeakWord] = []
    if items:
        rows = (
            await db.execute(
                select(
                    ev.lexicon_item_id,
                    func.count(),
                    func.max(ev.occurred_at),
                    func.array_agg(func.distinct(ev.error_tag)),
                )
                .join(LearningSession, LearningSession.id == ev.session_id)
                .where(
                    ev.user_id == user.id,
                    ev.lexicon_item_id.in_([i.id for i in items]),
                    LearningSession.mode.in_([SessionMode.CHECK, SessionMode.EXAM]),
                    ev.is_correct.is_(False),
                    ev.occurred_at >= since,
                )
                .group_by(ev.lexicon_item_id)
            )
        ).all()
        stats = {r[0]: r[1:] for r in rows}
        for i in items:
            n, last, tags = stats.get(i.id, (0, since, []))
            words.append(WeakWord(i, n, last, sorted(t for t in tags if t)))
        words.sort(key=lambda w: (-w.errors, -w.last_error_at.timestamp()))

    ga = GrammarAttempt
    unit_rows = (
        await db.execute(
            select(
                GrammarUnit, func.count(), func.max(ga.occurred_at), func.array_agg(ga.error_tag)
            )
            .join(GrammarUnit, GrammarUnit.id == ga.unit_id)
            .where(
                ga.user_id == user.id,
                GrammarUnit.language == language,
                GrammarUnit.active.is_(True),
                ga.mode == "check",
                ga.is_correct.is_(False),
                ga.occurred_at >= since,
            )
            .group_by(GrammarUnit.id)
            .order_by(func.count().desc(), func.max(ga.occurred_at).desc())
            .limit(limit)
        )
    ).all()
    units = [WeakUnit(u, n, last, sorted({t for t in tags if t})) for u, n, last, tags in unit_rows]

    # Mistake kinds across both logs (lesson practice excluded).
    tag_counts: Counter[str] = Counter()
    for tag, n in (
        await db.execute(
            select(ev.error_tag, func.count())
            .join(LexiconItem, LexiconItem.id == ev.lexicon_item_id)
            .join(LearningSession, LearningSession.id == ev.session_id)
            .where(
                ev.user_id == user.id,
                LexiconItem.language == language,
                LearningSession.mode.in_([SessionMode.CHECK, SessionMode.EXAM]),
                ev.error_tag.is_not(None),
                ev.occurred_at >= since,
                _suitable(user),
            )
            .group_by(ev.error_tag)
        )
    ).all():
        tag_counts[tag] += n
    for tag, n in (
        await db.execute(
            select(ga.error_tag, func.count())
            .join(GrammarUnit, GrammarUnit.id == ga.unit_id)
            .where(
                ga.user_id == user.id,
                GrammarUnit.language == language,
                ga.mode == "check",
                ga.error_tag.is_not(None),
                ga.occurred_at >= since,
            )
            .group_by(ga.error_tag)
        )
    ).all():
        tag_counts[tag] += n
    return WeakSpots(words, units, tag_counts.most_common(), POLICY.remediation_window.days)
