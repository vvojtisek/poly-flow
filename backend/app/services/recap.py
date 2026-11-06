"""Weekly recap for one language: the last seven local days against the seven before. Read-only."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Language
from app.domain.recap import Week, suggest, trend
from app.models import LearningEvent, LexiconItem, User, UserWordProgress

HARD_WORDS = 3


async def _week(db: AsyncSession, user: User, language: Language, first, last, tz) -> Week:
    ev, li, p = LearningEvent, LexiconItem, UserWordProgress
    days, graded, correct, practice = (
        await db.execute(
            select(
                func.count(func.distinct(ev.local_date)),
                func.count().filter(ev.counts_as_evidence.is_(True)),
                func.count().filter(ev.counts_as_evidence.is_(True), ev.is_correct.is_(True)),
                func.count().filter(ev.counts_as_evidence.is_(False)),
            )
            .join(li, li.id == ev.lexicon_item_id)
            .where(
                ev.user_id == user.id,
                li.language == language,
                ev.local_date >= first,
                ev.local_date <= last,
            )
        )
    ).one()
    start = datetime.combine(first, time.min, tz)
    end = datetime.combine(last + timedelta(days=1), time.min, tz)
    introduced, known = (
        await db.execute(
            select(
                func.count().filter(p.introduced_at >= start, p.introduced_at < end),
                func.count().filter(p.known_since_at >= start, p.known_since_at < end),
            )
            .join(li, li.id == p.lexicon_item_id)
            .where(p.user_id == user.id, li.language == language)
        )
    ).one()
    return Week(days, graded, correct, practice, introduced, known)


async def recap(db: AsyncSession, user: User, language: Language, now: datetime) -> dict:
    tz = ZoneInfo(user.timezone)
    today = now.astimezone(tz).date()
    first = today - timedelta(days=6)
    this = await _week(db, user, language, first, today, tz)
    before = await _week(
        db, user, language, first - timedelta(days=7), first - timedelta(days=1), tz
    )

    ev, li, p = LearningEvent, LexiconItem, UserWordProgress
    hard = (
        await db.execute(
            select(li.id, li.lemma, li.gender, li.translation_cs, func.count().label("misses"))
            .join(ev, ev.lexicon_item_id == li.id)
            .where(
                ev.user_id == user.id,
                li.language == language,
                ev.counts_as_evidence.is_(True),
                ev.is_correct.is_(False),
                ev.local_date >= first,
            )
            .group_by(li.id)
            .order_by(func.count().desc(), li.frequency_rank)
            .limit(HARD_WORDS)
        )
    ).all()
    due_now, due_week = (
        await db.execute(
            select(
                func.count().filter(p.next_review_at <= now),
                func.count().filter(p.next_review_at <= now + timedelta(days=7)),
            )
            .join(li, li.id == p.lexicon_item_id)
            .where(
                p.user_id == user.id,
                li.language == language,
                p.introduced_at.is_not(None),
                p.next_review_at.is_not(None),
            )
        )
    ).one()
    return {
        "language": language,
        "from": first,
        "to": today,
        "this_week": this,
        "last_week": before,
        "accuracy_trend": trend(this.accuracy, before.accuracy),
        "hard_words": [
            {
                "id": r.id,
                "lemma": r.lemma,
                "gender": r.gender,
                "translation": r.translation_cs,
                "misses": r.misses,
            }
            for r in hard
        ],
        "due_now": due_now,
        "due_next_7_days": due_week,
        "suggestion": suggest(this, due_now, len(hard)),
    }
