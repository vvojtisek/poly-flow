"""Today's plan (Dnešní plán): the next sensible steps in a fixed, explainable order.

1. Ověření of words that are due (memory first: due reviews lose the most when they wait).
2. Ověření gramatiky for due grammar topics.
3. A Lekce with new words (when there are words not yet introduced).
4. Reading (a short story) once some words are known.

Time today is an estimate from the answers given (no timers run while learning). The daily goal
is the profile's own `daily_goal_minutes`; missing it has no consequence and nothing is counted in
a row.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Language
from app.models import (
    GrammarAttempt,
    GrammarUnit,
    LearningEvent,
    LexiconItem,
    User,
    UserWordProgress,
)
from app.services import grammar as grammar_svc
from app.services.learning import _suitable

# Seconds per answer, a rough average from the lesson design (reading the task, answering,
# reading the feedback). An estimate, labelled as such in the UI.
SECONDS = {"graded": 9, "practice": 12, "grammar": 20}
CHECK_CAP = 20  # one check session asks at most this many words
LESSON_WORDS = 4


async def plan(db: AsyncSession, user: User, language: Language, now: datetime) -> dict:
    tz = ZoneInfo(user.timezone)
    today = now.astimezone(tz).date()
    p, li = UserWordProgress, LexiconItem
    due_words, known = (
        await db.execute(
            select(
                func.count().filter(p.introduced_at.is_not(None), p.next_review_at <= now),
                func.count().filter(p.passive_known.is_(True)),
            )
            .select_from(p)
            .join(li, li.id == p.lexicon_item_id)
            .where(p.user_id == user.id, li.language == language)
        )
    ).one()
    new_words = await db.scalar(
        select(func.count())
        .select_from(li)
        .outerjoin(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
        .where(li.language == language, _suitable(user), p.introduced_at.is_(None))
    )
    due_grammar = await grammar_svc.due_count(db, user, language, now)

    graded, practice = (
        await db.execute(
            select(
                func.count().filter(LearningEvent.counts_as_evidence.is_(True)),
                func.count().filter(LearningEvent.counts_as_evidence.is_(False)),
            )
            .select_from(LearningEvent)
            .join(li, li.id == LearningEvent.lexicon_item_id)
            .where(LearningEvent.user_id == user.id, LearningEvent.local_date == today)
        )
    ).one()
    grammar_answers = await db.scalar(
        select(func.count())
        .select_from(GrammarAttempt)
        .join(GrammarUnit, GrammarUnit.id == GrammarAttempt.unit_id)
        .where(GrammarAttempt.user_id == user.id, GrammarAttempt.local_date == today)
    )
    seconds = (
        graded * SECONDS["graded"]
        + practice * SECONDS["practice"]
        + (grammar_answers or 0) * SECONDS["grammar"]
    )
    goal = int((user.settings or {}).get("daily_goal_minutes", 10))

    steps = []
    if due_words:
        n = min(due_words, CHECK_CAP)
        steps.append({"kind": "check", "count": due_words, "minutes": max(1, round(n * 9 / 60))})
    if due_grammar:
        steps.append(
            {"kind": "grammar_check", "count": due_grammar, "minutes": max(1, due_grammar)}
        )
    if new_words:
        steps.append({"kind": "lesson", "count": min(new_words, LESSON_WORDS), "minutes": 5})
    if known >= 20:
        steps.append({"kind": "reading", "count": 1, "minutes": 5})
    return {
        "language": language,
        "date": today,
        "minutes_today": round(seconds / 60),
        "answers_today": graded + practice + (grammar_answers or 0),
        "goal_minutes": goal,
        "steps": steps,
        "tomorrow_due": await _due_by(db, user, language, now, tz, today + timedelta(days=1)),
    }


async def _due_by(db, user, language, now, tz, day) -> int:
    end = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=tz)
    p, li = UserWordProgress, LexiconItem
    return (
        await db.scalar(
            select(func.count())
            .select_from(p)
            .join(li, li.id == p.lexicon_item_id)
            .where(
                p.user_id == user.id,
                li.language == language,
                p.introduced_at.is_not(None),
                p.next_review_at > now,
                p.next_review_at < end,
            )
        )
        or 0
    )
