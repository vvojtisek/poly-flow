"""Personal mastery ranks and achievements: measure the evidence, record what was reached.

Rules live in `app.domain.ranks`. Callers own the transaction.
"""

from datetime import datetime

from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.domain.enums import CefrLevel, Language
from app.domain.ranks import ACHIEVEMENTS, MAX_RANK, RANKS, Stats, held_rank, progress_to
from app.models import (
    GrammarAttempt,
    GrammarUnit,
    LearningEvent,
    LevelBadge,
    LexiconItem,
    MasteryAward,
    User,
    UserGrammarProgress,
    UserWordProgress,
)

RANK, ACHIEVEMENT = "rank", "achievement"


async def stats(db: AsyncSession, user: User, language: Language) -> Stats:
    p, li = UserWordProgress, LexiconItem
    known, passive = (
        await db.execute(
            select(
                func.count().filter(p.passive_known.is_(True), p.active_known.is_(True)),
                func.count().filter(p.passive_known.is_(True)),
            )
            .select_from(p)
            .join(li, li.id == p.lexicon_item_id)
            .where(p.user_id == user.id, li.language == language)
        )
    ).one()
    gp, gu = UserGrammarProgress, GrammarUnit
    grammar_known = await db.scalar(
        select(func.count())
        .select_from(gp)
        .join(gu, gu.id == gp.unit_id)
        .where(
            gp.user_id == user.id,
            gu.language == language,
            gu.active.is_(True),
            gp.known_since_at.is_not(None),
        )
    )
    grammar_total = await db.scalar(
        select(func.count()).where(gu.language == language, gu.active.is_(True))
    )
    badges = frozenset(
        (
            await db.execute(
                select(LevelBadge.level).where(
                    LevelBadge.user_id == user.id, LevelBadge.language == language
                )
            )
        ).scalars()
    )
    # Recovered mistakes: missed in a check, answered right in a later check.
    e1, e2 = aliased(LearningEvent), aliased(LearningEvent)
    word_recoveries = await db.scalar(
        select(func.count(func.distinct(e1.lexicon_item_id)))
        .join(li, li.id == e1.lexicon_item_id)
        .join(
            e2,
            and_(
                e2.user_id == e1.user_id,
                e2.lexicon_item_id == e1.lexicon_item_id,
                e2.counts_as_evidence.is_(True),
                e2.is_correct.is_(True),
                e2.occurred_at > e1.occurred_at,
            ),
        )
        .where(
            e1.user_id == user.id,
            li.language == language,
            e1.counts_as_evidence.is_(True),
            e1.is_correct.is_(False),
        )
    )
    g1, g2 = aliased(GrammarAttempt), aliased(GrammarAttempt)
    grammar_recoveries = await db.scalar(
        select(func.count(func.distinct(g1.exercise_id)))
        .join(gu, gu.id == g1.unit_id)
        .join(
            g2,
            and_(
                g2.user_id == g1.user_id,
                g2.exercise_id == g1.exercise_id,
                g2.counts_as_evidence.is_(True),
                g2.is_correct.is_(True),
                g2.occurred_at > g1.occurred_at,
            ),
        )
        .where(
            g1.user_id == user.id,
            gu.language == language,
            g1.counts_as_evidence.is_(True),
            g1.is_correct.is_(False),
        )
    )
    word_checks, spoken_right = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(
                    LearningEvent.answer_mode == "spoken", LearningEvent.is_correct.is_(True)
                ),
            )
            .select_from(LearningEvent)
            .join(li, li.id == LearningEvent.lexicon_item_id)
            .where(
                LearningEvent.user_id == user.id,
                li.language == language,
                LearningEvent.counts_as_evidence.is_(True),
            )
        )
    ).one()
    grammar_checks = await db.scalar(
        select(func.count())
        .select_from(GrammarAttempt)
        .join(gu, gu.id == GrammarAttempt.unit_id)
        .where(
            GrammarAttempt.user_id == user.id,
            gu.language == language,
            GrammarAttempt.counts_as_evidence.is_(True),
        )
    )
    return Stats(
        known_words=known or 0,
        passive_words=passive or 0,
        grammar_known=grammar_known or 0,
        grammar_total=grammar_total or 0,
        badges=frozenset(CefrLevel(b) for b in badges),
        recoveries=(word_recoveries or 0) + (grammar_recoveries or 0),
        checks_answered=(word_checks or 0) + (grammar_checks or 0),
        listening_right=spoken_right or 0,
    )


async def _awards(db: AsyncSession, user: User, language: Language) -> list[MasteryAward]:
    return list(
        (
            await db.execute(
                select(MasteryAward).where(
                    MasteryAward.user_id == user.id, MasteryAward.language == language
                )
            )
        ).scalars()
    )


async def overview(db: AsyncSession, user: User, language: Language, now: datetime) -> dict:
    """Current rank, the next one's requirements, achievements; records anything newly reached."""
    s = await stats(db, user, language)
    awards = await _awards(db, user, language)
    recorded = max((int(a.key) for a in awards if a.kind == RANK), default=0)
    rank = held_rank(s, recorded)
    new_rows = [
        {"kind": RANK, "key": str(n), "seen_at": now if n == 1 else None}
        for n in range(1, rank + 1)
        if n > recorded
    ]
    have = {a.key for a in awards if a.kind == ACHIEVEMENT}
    new_rows += [
        {"kind": ACHIEVEMENT, "key": a.key, "seen_at": None}
        for a in ACHIEVEMENTS
        if a.key not in have and a.earned(s)
    ]
    if new_rows:
        await db.execute(
            pg_insert(MasteryAward)
            .values(
                [
                    {"user_id": user.id, "language": language, "reached_at": now, **row}
                    for row in new_rows
                ]
            )
            .on_conflict_do_nothing()
        )
        awards = await _awards(db, user, language)
    by_key = {(a.kind, a.key): a for a in awards}
    nxt = RANKS[rank] if rank < MAX_RANK else None
    unseen_rank = max(
        (int(a.key) for a in awards if a.kind == RANK and a.seen_at is None), default=None
    )
    return {
        "language": language,
        "path": (user.settings or {}).get("rank_path", "hockey"),
        "rank": rank,
        "max_rank": MAX_RANK,
        "tier": RANKS[rank - 1].tier,
        "next": {"rank": nxt.number, "tier": nxt.tier, "requirements": progress_to(nxt, s)}
        if nxt
        else None,
        "ranks": [
            {
                "rank": r.number,
                "tier": r.tier,
                "reached_at": by_key[(RANK, str(r.number))].reached_at
                if (RANK, str(r.number)) in by_key
                else None,
                "requirements": progress_to(r, s),
            }
            for r in RANKS
        ],
        "achievements": [
            {
                "key": a.key,
                "group": a.group,
                "reached_at": by_key[(ACHIEVEMENT, a.key)].reached_at
                if (ACHIEVEMENT, a.key) in by_key
                else None,
            }
            for a in ACHIEVEMENTS
        ],
        "unseen_rank": unseen_rank,
        "unseen_achievements": [
            a.key for a in awards if a.kind == ACHIEVEMENT and a.seen_at is None
        ],
        "stats": {
            "known_words": s.known_words,
            "passive_words": s.passive_words,
            "grammar_known": s.grammar_known,
            "grammar_total": s.grammar_total,
            "recoveries": s.recoveries,
            "checks_answered": s.checks_answered,
            "badges": sorted(b.value for b in s.badges),
        },
    }


async def mark_seen(db: AsyncSession, user: User, language: Language, now: datetime) -> None:
    """The celebration was shown: every award reached so far counts as seen."""
    await db.execute(
        update(MasteryAward)
        .where(
            MasteryAward.user_id == user.id,
            MasteryAward.language == language,
            MasteryAward.seen_at.is_(None),
        )
        .values(seen_at=now)
    )
