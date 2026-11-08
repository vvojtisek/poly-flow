"""Apply aggregate level-test completion while preserving individual answer history."""

from datetime import datetime

from sqlalchemy import func, literal, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import CefrLevel, Language, ProgressState
from app.domain.level_exam import prerequisite_rank_ceiling
from app.models import GrammarUnit, LexiconItem, User, UserGrammarProgress, UserWordProgress
from app.services import learning as lsvc


async def complete_through(
    db: AsyncSession,
    user: User,
    language: Language,
    level: CefrLevel,
    now: datetime,
) -> None:
    """Mark available words/rules through a passed level, without creating fake answer events."""
    ceiling = prerequisite_rank_ceiling(level)
    eligible_words = select(LexiconItem.id).where(
        LexiconItem.language == language,
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
                LexiconItem.language == language,
                LexiconItem.frequency_rank <= ceiling,
                lsvc._suitable(user),
            ),
        )
        .on_conflict_do_nothing(constraint="uq_user_word_progress_user_item")
    )

    eligible_units = select(GrammarUnit.id).where(
        GrammarUnit.language == language,
        GrammarUnit.level <= level,
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
                GrammarUnit.language == language,
                GrammarUnit.level <= level,
                GrammarUnit.active.is_(True),
            ),
        )
        .on_conflict_do_nothing()
    )
