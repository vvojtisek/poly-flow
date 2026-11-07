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
from app.models.learning import TaskType
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

    # First-try accuracy per ISO week (graded answers only), kept apart per skill: recognising a
    # word, producing it, and grammar are different abilities, and one average would hide which
    # of them is moving.
    week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=ACCURACY_WEEKS - 1)
    skills = ("recognition", "recall", "grammar")
    weeks: dict[date, dict[str, list[int]]] = {
        week_start + timedelta(weeks=i): {k: [0, 0] for k in skills} for i in range(ACCURACY_WEEKS)
    }
    wk = cast(func.date_trunc("week", ev.local_date), Date)
    rows = await db.execute(
        select(wk, ev.task_type, func.count(), func.count().filter(ev.is_correct.is_(True)))
        .join(li, li.id == ev.lexicon_item_id)
        .where(
            ev.user_id == user.id,
            li.language == language,
            ev.counts_as_evidence.is_(True),
            ev.local_date >= week_start,
        )
        .group_by(wk, ev.task_type)
    )
    for w, task, n, ok in rows.all():
        if w in weeks:
            skill = "recall" if task == TaskType.RECALL else "recognition"
            weeks[w][skill][0] += n
            weeks[w][skill][1] += ok
    gwk = cast(func.date_trunc("week", ga.local_date), Date)
    rows = await db.execute(
        select(gwk, func.count(), func.count().filter(ga.is_correct.is_(True)))
        .join(gu, gu.id == ga.unit_id)
        .where(
            ga.user_id == user.id,
            gu.language == language,
            ga.counts_as_evidence.is_(True),
            ga.local_date >= week_start,
        )
        .group_by(gwk)
    )
    for w, n, ok in rows.all():
        if w in weeks:
            weeks[w]["grammar"][0] += n
            weeks[w]["grammar"][1] += ok

    # Mistake types in graded answers, each with the words and topics behind it (most frequent
    # first), so a learner can go from "gender: 7" to the nouns that cause it.
    tags: dict[str, int] = defaultdict(int)
    behind: dict[str, list[dict]] = defaultdict(list)
    mistake_since = today - timedelta(days=MISTAKE_DAYS)
    missed = (
        ev.user_id == user.id,
        li.language == language,
        ev.counts_as_evidence.is_(True),
        ev.is_correct.is_(False),
        ev.error_tag.is_not(None),
        ev.local_date >= mistake_since,
    )
    rows = await db.execute(
        select(ev.error_tag, li.id, li.lemma, li.gender, li.translation_cs, func.count())
        .join(li, li.id == ev.lexicon_item_id)
        .where(*missed, _suitable(user))
        .group_by(ev.error_tag, li.id)
    )
    for tag, item_id, lemma, gender, translation, n in rows.all():
        tags[tag] += n
        behind[tag].append(
            {
                "kind": "word",
                "id": item_id,
                "label": f"{gender} {lemma}" if gender and len(gender) > 1 else lemma,
                "detail": translation,
                "count": n,
            }
        )
    rows = await db.execute(
        select(ga.error_tag, gu.id, gu.title, gu.level, func.count())
        .join(gu, gu.id == ga.unit_id)
        .where(
            ga.user_id == user.id,
            gu.language == language,
            ga.counts_as_evidence.is_(True),
            ga.is_correct.is_(False),
            ga.error_tag.is_not(None),
            ga.local_date >= mistake_since,
        )
        .group_by(ga.error_tag, gu.id)
    )
    for tag, unit_id, title, level, n in rows.all():
        tags[tag] += n
        behind[tag].append(
            {"kind": "grammar", "id": unit_id, "label": title, "detail": level, "count": n}
        )

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
        "accuracy": [
            {
                "week": w,
                "answered": sum(v[0] for v in by.values()),
                "correct": sum(v[1] for v in by.values()),
                **{k: {"answered": v[0], "correct": v[1]} for k, v in by.items()},
            }
            for w, by in weeks.items()
        ],
        "mistakes": sorted(
            (
                {
                    "tag": t,
                    "count": n,
                    "items": sorted(behind[t], key=lambda x: (-x["count"], x["label"]))[:6],
                }
                for t, n in tags.items()
            ),
            key=lambda x: -x["count"],
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


async def day_activity(
    db: AsyncSession, user: User, language: Language, activity_date: date, now: datetime
) -> dict | None:
    """Read-only, answer-free details for one calendar day in the learner's heatmap."""
    today = now.astimezone(ZoneInfo(user.timezone)).date()
    if not today - timedelta(days=HEATMAP_DAYS - 1) <= activity_date <= today:
        return None

    ev, li = LearningEvent, LexiconItem
    words = await db.execute(
        select(
            li.id,
            li.lemma,
            li.gender,
            li.translation_cs,
            func.count().filter(ev.counts_as_evidence.is_(True)),
            func.count().filter(ev.counts_as_evidence.is_(False)),
        )
        .join(li, li.id == ev.lexicon_item_id)
        .where(
            ev.user_id == user.id,
            li.language == language,
            ev.local_date == activity_date,
            _suitable(user),
        )
        .group_by(li.id)
        .order_by(li.frequency_rank, li.lemma)
    )
    ga, gu = GrammarAttempt, GrammarUnit
    grammar = await db.execute(
        select(
            gu.id,
            gu.title,
            gu.level,
            func.count().filter(ga.counts_as_evidence.is_(True)),
            func.count().filter(ga.counts_as_evidence.is_(False)),
        )
        .join(gu, gu.id == ga.unit_id)
        .where(
            ga.user_id == user.id,
            gu.language == language,
            gu.active.is_(True),
            ga.local_date == activity_date,
        )
        .group_by(gu.id)
        .order_by(gu.level, gu.title)
    )
    return {
        "date": activity_date,
        "words": [
            {
                "id": item_id,
                "lemma": lemma,
                "gender": gender,
                "translation": translation,
                "graded": graded,
                "practice": practice,
            }
            for item_id, lemma, gender, translation, graded, practice in words.all()
        ],
        "grammar": [
            {
                "id": unit_id,
                "title": title,
                "level": level,
                "graded": graded,
                "practice": practice,
            }
            for unit_id, title, level, graded, practice in grammar.all()
        ],
    }
