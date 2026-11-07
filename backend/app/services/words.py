"""My dictionary (Můj slovník): the words a profile has met, with their state and history.

Only words with a progress row (seen in a lesson, a test or a check) are listed: the dictionary
is the learner's own, not a way around the lessons. The content filter applies as everywhere.
"""

import uuid
from datetime import datetime

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.domain.enums import Language, ProgressState
from app.domain.export import Row
from app.domain.progression import vocabulary_level, vocabulary_levels
from app.models import (
    LearningEvent,
    LexiconItem,
    Scene,
    SceneWord,
    User,
    UserWordProgress,
    WordCollection,
    WordCollectionItem,
)
from app.services.learning import LearningError, _suitable
from app.services.notes import notes_for

DECK_LIMIT = 50

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
    level: str | None = None,
    topic: uuid.UUID | None = None,
) -> dict:
    p, li = UserWordProgress, LexiconItem
    st = _status().label("status")
    scope = await _scope(db, user, language, level, topic)
    base = (
        select(li, p, st)
        .join(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
        .where(li.language == language, _suitable(user), *scope)
    )
    counts = dict(
        (
            await db.execute(
                select(st, func.count())
                .select_from(li)
                .join(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
                .where(li.language == language, _suitable(user), *scope)
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


async def export_rows(db: AsyncSession, user: User, language: Language) -> list[Row]:
    """Every word this profile has met in the language, for its own export (frequency order)."""
    p, li = UserWordProgress, LexiconItem
    rows = (
        await db.execute(
            select(li, p, _status())
            .join(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
            .where(li.language == language, _suitable(user))
            .order_by(li.frequency_rank)
        )
    ).all()
    notes = await notes_for(db, user.id, [item.id for item, _, _ in rows])
    return [
        _export_row(item, prog, status, language, notes.get(item.id)) for item, prog, status in rows
    ]


async def export_collection_rows(
    db: AsyncSession, user: User, collection_id: uuid.UUID
) -> tuple[Language, list[Row]]:
    collection = await db.scalar(
        select(WordCollection).where(
            WordCollection.id == collection_id, WordCollection.user_id == user.id
        )
    )
    if collection is None:
        raise LearningError("collection_not_found", 404)
    p, li = UserWordProgress, LexiconItem
    rows = (
        await db.execute(
            select(li, p, _status())
            .join(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
            .join(WordCollectionItem, WordCollectionItem.lexicon_item_id == li.id)
            .where(
                WordCollectionItem.collection_id == collection.id,
                li.language == collection.language,
                _suitable(user),
            )
            .order_by(li.frequency_rank)
        )
    ).all()
    notes = await notes_for(db, user.id, [item.id for item, _, _ in rows])
    return collection.language, [
        _export_row(item, prog, status, collection.language, notes.get(item.id))
        for item, prog, status in rows
    ]


def _export_row(item, prog, status: str, language: Language, note: str | None) -> Row:
    return Row(
        lemma=item.lemma,
        article=item.gender if language == Language.DE and item.pos == "NOUN" else None,
        translation=item.translation_cs,
        status=status,
        pos=item.pos,
        rank=item.frequency_rank,
        example=item.example_sentence,
        note=note,
        next_review=prog.next_review_at.date().isoformat() if prog.next_review_at else None,
        correct=prog.correct_count,
        errors=prog.error_count,
        source=item.source,
    )


# ---------------------------------------------------------------- groups and scoped flashcards
# Levels group words by frequency rank (indicative CEFR, app.domain.progression); topics are the
# lesson scenes, the reviewed thematic grouping the curriculum has. Counts and decks cover only
# the profile's own words (a progress row), like the rest of the dictionary: flashcards repeat
# what lessons introduced, they do not replace the lesson's context-first introduction.


def _scene_ok(user: User):
    """A scene with a word this profile does not get is hidden as a whole, as in lessons."""
    hidden = aliased(LexiconItem)
    return ~(
        select(SceneWord.scene_id)
        .join(hidden, hidden.id == SceneWord.lexicon_item_id)
        .where(SceneWord.scene_id == Scene.id, ~_suitable(user, hidden))
        .exists()
    )


async def _scope(
    db: AsyncSession, user: User, language: Language, level: str | None, topic: uuid.UUID | None
) -> list:
    """Filters for one vocabulary level and/or one lesson topic (validated; unknown -> error)."""
    li = LexiconItem
    out: list = []
    if level is not None:
        bounds = {key: (lo, hi) for key, lo, hi in vocabulary_levels()}
        if level not in bounds:
            raise LearningError("unknown_level", 422)
        lo, hi = bounds[level]
        out.append(li.frequency_rank >= lo)
        if hi is not None:
            out.append(li.frequency_rank <= hi)
    if topic is not None:
        found = (
            await db.execute(
                select(Scene.id).where(
                    Scene.id == topic, Scene.language == language, _scene_ok(user)
                )
            )
        ).scalar_one_or_none()
        if found is None:
            raise LearningError("topic_not_found", 404)
        out.append(li.id.in_(select(SceneWord.lexicon_item_id).where(SceneWord.scene_id == topic)))
    return out


async def word_groups(db: AsyncSession, user: User, language: Language) -> dict:
    p, li = UserWordProgress, LexiconItem
    on = and_(p.lexicon_item_id == li.id, p.user_id == user.id)
    by_band = (
        await db.execute(
            select(li.frequency_band, func.count(li.id), func.count(p.lexicon_item_id))
            .outerjoin(p, on)
            .where(li.language == language, _suitable(user))
            .group_by(li.frequency_band)
        )
    ).all()
    totals: dict[str, list[int]] = {key: [0, 0] for key, _, _ in vocabulary_levels()}
    for band, total, mine in by_band:
        counts = totals[vocabulary_level(band)]
        counts[0] += total
        counts[1] += mine
    levels = [
        {
            "key": key,
            "first_rank": lo,
            "last_rank": hi,
            "total": totals[key][0],
            "mine": totals[key][1],
        }
        for key, lo, hi in vocabulary_levels()
        if totals[key][0] > 0
    ]
    topics = (
        await db.execute(
            select(Scene.id, Scene.title_cs, func.count(li.id), func.count(p.lexicon_item_id))
            .join(SceneWord, SceneWord.scene_id == Scene.id)
            .join(li, li.id == SceneWord.lexicon_item_id)
            .outerjoin(p, on)
            .where(Scene.language == language, _scene_ok(user))
            .group_by(Scene.id, Scene.title_cs, Scene.position)
            .order_by(Scene.position)
        )
    ).all()
    return {
        "levels": levels,
        "topics": [
            {"id": sid, "title": title, "total": total, "mine": mine}
            for sid, title, total, mine in topics
        ],
    }


async def word_deck(
    db: AsyncSession,
    user: User,
    language: Language,
    now: datetime,
    *,
    level: str | None,
    topic: uuid.UUID | None,
    weak: bool = False,
    limit: int = DECK_LIMIT,
) -> dict:
    """The profile's own words in one scope (a level, a topic, or its unresolved check mistakes),
    due and unfinished words first."""
    if sum((level is not None, topic is not None, weak)) != 1:
        raise LearningError("deck_scope_required", 422)
    p, li = UserWordProgress, LexiconItem
    if weak:
        from app.services import mistakes

        missed = [w.item.id for w in (await mistakes.weak_spots(db, user, language, now)).words]
        scope = [li.id.in_(missed)]
    else:
        scope = await _scope(db, user, language, level, topic)
    st = _status().label("status")
    due = and_(p.introduced_at.is_not(None), p.next_review_at <= now)
    q = (
        select(li, p, st)
        .join(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
        .where(
            li.language == language,
            _suitable(user),
            *scope,
        )
    )
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (
        await db.execute(
            q.order_by(
                case((due, 0), else_=1),
                case((p.state == ProgressState.MASTERED, 1), else_=0),
                li.frequency_rank,
            ).limit(limit)
        )
    ).all()
    return {
        "total": total,
        "items": [
            {
                "id": item.id,
                "lemma": item.lemma,
                "gender": item.gender,
                "pos": item.pos,
                "rank": item.frequency_rank,
                "translation": item.translation_cs,
                "example": item.example_sentence,
                "status": status,
                "due": prog.introduced_at is not None
                and prog.next_review_at is not None
                and prog.next_review_at <= now,
            }
            for item, prog, status in rows
        ],
    }
