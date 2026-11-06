"""Learning insights: activity, accuracy, mistakes and the review forecast for one language.

Read-only aggregates over the learner's own events. Activity is shown as a calendar, never as a
streak: nothing here rewards or punishes a day off.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Language, ProgressState
from app.models import (
    GrammarAttempt,
    GrammarUnit,
    LearningEvent,
    LexiconItem,
    User,
    UserGrammarProgress,
    UserWordProgress,
)
from app.services.learning import _suitable

HEATMAP_DAYS = 182
ACCURACY_WEEKS = 12
MISTAKE_DAYS = 60
FORECAST_DAYS = 14


async def insights(db: AsyncSession, user: User, language: Language, now: datetime) -> dict:
    tz = ZoneInfo(user.timezone)
    today = now.astimezone(tz).date()
    since = today - timedelta(days=HEATMAP_DAYS - 1)
    ev, li = LearningEvent, LexiconItem
    ga, gu = GrammarAttempt, GrammarUnit

    days: dict[date, dict[str, int]] = defaultdict(lambda: {"graded": 0, "practice": 0})
    rows = await db.execute(
        select(ev.local_date, ev.counts_as_evidence, func.count())
        .join(li, li.id == ev.lexicon_item_id)
        .where(ev.user_id == user.id, li.language == language, ev.local_date >= since)
        .group_by(ev.local_date, ev.counts_as_evidence)
    )
    for d, graded, n in rows.all():
        days[d]["graded" if graded else "practice"] += n
    rows = await db.execute(
        select(ga.local_date, ga.counts_as_evidence, func.count())
        .join(gu, gu.id == ga.unit_id)
        .where(ga.user_id == user.id, gu.language == language, ga.local_date >= since)
        .group_by(ga.local_date, ga.counts_as_evidence)
    )
    for d, graded, n in rows.all():
        days[d]["graded" if graded else "practice"] += n

    # First-try accuracy per ISO week (graded answers only).
    week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=ACCURACY_WEEKS - 1)
    weeks: dict[date, list[int]] = {
        week_start + timedelta(weeks=i): [0, 0] for i in range(ACCURACY_WEEKS)
    }
    for model, join_on, lang_col in (
        (ev, li.id == ev.lexicon_item_id, li.language),
        (ga, gu.id == ga.unit_id, gu.language),
    ):
        target = li if model is ev else gu
        wk = cast(func.date_trunc("week", model.local_date), Date)
        rows = await db.execute(
            select(wk, func.count(), func.count().filter(model.is_correct.is_(True)))
            .join(target, join_on)
            .where(
                model.user_id == user.id,
                lang_col == language,
                model.counts_as_evidence.is_(True),
                model.local_date >= week_start,
            )
            .group_by(wk)
        )
        for w, n, ok in rows.all():
            if w in weeks:
                weeks[w][0] += n
                weeks[w][1] += ok

    # Mistake types in graded answers.
    tags: dict[str, int] = defaultdict(int)
    mistake_since = today - timedelta(days=MISTAKE_DAYS)
    for model, target, join_on, lang_col in (
        (ev, li, li.id == ev.lexicon_item_id, li.language),
        (ga, gu, gu.id == ga.unit_id, gu.language),
    ):
        rows = await db.execute(
            select(model.error_tag, func.count())
            .join(target, join_on)
            .where(
                model.user_id == user.id,
                lang_col == language,
                model.counts_as_evidence.is_(True),
                model.is_correct.is_(False),
                model.error_tag.is_not(None),
                model.local_date >= mistake_since,
            )
            .group_by(model.error_tag)
        )
        for tag, n in rows.all():
            tags[tag] += n

    # Review forecast: words and grammar topics due per local day (overdue counts as today).
    p, gp = UserWordProgress, UserGrammarProgress
    horizon = now + timedelta(days=FORECAST_DAYS)
    forecast = {
        today + timedelta(days=i): {"words": [], "grammar": []} for i in range(FORECAST_DAYS)
    }
    word_due = await db.execute(
        select(li.id, li.lemma, li.gender, li.translation_cs, p.next_review_at)
        .join(li, li.id == p.lexicon_item_id)
        .where(
            p.user_id == user.id,
            li.language == language,
            _suitable(user),
            p.introduced_at.is_not(None),
            p.next_review_at.is_not(None),
            p.next_review_at < horizon,
        )
    )
    for item_id, lemma, gender, translation, at in word_due.all():
        d = max(at.astimezone(tz).date(), today)
        if d in forecast:
            forecast[d]["words"].append(
                {"id": item_id, "lemma": lemma, "gender": gender, "translation": translation}
            )
    grammar_due = await db.execute(
        select(gu.id, gu.title, gu.level, gp.next_review_at)
        .join(gu, gu.id == gp.unit_id)
        .where(
            gp.user_id == user.id,
            gu.language == language,
            gu.active.is_(True),
            gp.studied_at.is_not(None),
            gp.next_review_at.is_not(None),
            gp.next_review_at < horizon,
        )
    )
    for unit_id, title, level, at in grammar_due.all():
        d = max(at.astimezone(tz).date(), today)
        if d in forecast:
            forecast[d]["grammar"].append({"id": unit_id, "title": title, "level": level})

    # Knowledge funnel.
    introduced, passive, active, known, mastered = (
        await db.execute(
            select(
                func.count().filter(p.introduced_at.is_not(None)),
                func.count().filter(p.passive_known.is_(True)),
                func.count().filter(p.active_known.is_(True)),
                func.count().filter(p.passive_known.is_(True), p.active_known.is_(True)),
                func.count().filter(p.state == ProgressState.MASTERED),
            )
            .select_from(p)
            .join(li, li.id == p.lexicon_item_id)
            .where(p.user_id == user.id, li.language == language)
        )
    ).one()

    active_days = sum(1 for v in days.values() if v["graded"] + v["practice"] > 0)
    return {
        "language": language,
        "today": today,
        "heatmap": [
            {
                "date": since + timedelta(days=i),
                **days.get(since + timedelta(days=i), {"graded": 0, "practice": 0}),
            }
            for i in range(HEATMAP_DAYS)
        ],
        "active_days": active_days,
        "accuracy": [{"week": w, "answered": n, "correct": ok} for w, (n, ok) in weeks.items()],
        "mistakes": sorted(
            ({"tag": t, "count": n} for t, n in tags.items()), key=lambda x: -x["count"]
        ),
        "forecast": [
            {
                "date": d,
                "words": len(v["words"]),
                "grammar": len(v["grammar"]),
                "word_items": v["words"],
                "grammar_items": v["grammar"],
            }
            for d, v in forecast.items()
        ],
        "funnel": {
            "introduced": introduced,
            "passive": passive,
            "active": active,
            "known": known,
            "mastered": mastered,
        },
    }
