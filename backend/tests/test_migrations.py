"""Upgrading a database that already holds learner data must not lose or alter it."""

import subprocess

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from tests.conftest import alembic

SEED_0001 = [
    """INSERT INTO users (id, username, display_name)
       VALUES ('00000000-0000-0000-0000-000000000001', 'anna', 'Anna')""",
    """INSERT INTO lexicon_items (id, language, lemma, pos, frequency_rank, frequency_band,
                                 translation_cs)
       VALUES ('00000000-0000-0000-0000-0000000000a1', 'de', 'Haus', 'NOUN', 42, 100, 'dům')""",
    """INSERT INTO user_word_progress (id, user_id, lexicon_item_id, state, passive_known,
                                      phonetic_score, orthography_score, correct_count,
                                      last_error_free_at)
       VALUES ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-000000000001',
               '00000000-0000-0000-0000-0000000000a1', 'LEARNING', true, NULL, 0.75, 4,
               '2026-09-01T10:00:00Z')""",
]

CHECK = """
SELECT u.username, l.lemma, l.frequency_rank, p.state::text, p.passive_known, p.active_known,
       p.phonetic_score, p.orthography_score, p.correct_count, p.last_error_free_at
FROM user_word_progress p
JOIN users u ON u.id = p.user_id
JOIN lexicon_items l ON l.id = p.lexicon_item_id
"""


async def test_upgrade_from_0001_preserves_progress(migrated_db):
    alembic("downgrade", "base")
    alembic("upgrade", "0001")
    # NullPool: no connection may outlive a schema change with stale cached plans.
    engine = create_async_engine(migrated_db, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            for stmt in SEED_0001:
                await conn.execute(text(stmt))
            before = (await conn.execute(text(CHECK))).one()

        alembic("upgrade", "head")

        async with engine.begin() as conn:
            after = (await conn.execute(text(CHECK))).one()
        assert after == before
        assert after.phonetic_score is None  # "never measured" survives the upgrade
        async with engine.begin() as conn:
            introduced = (
                await conn.execute(text("SELECT introduced_at FROM user_word_progress"))
            ).scalar_one()
        assert introduced is not None  # v1-practised words stay checkable under v2
    finally:
        async with engine.begin() as conn:
            for table in ("user_word_progress", "lexicon_items", "users"):
                await conn.execute(text(f"DELETE FROM {table}"))
        await engine.dispose()
        alembic("upgrade", "head")


async def test_downgrade_below_0007_refuses_to_drop_english(migrated_db):
    engine = create_async_engine(migrated_db, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """INSERT INTO lexicon_items (id, language, lemma, pos, frequency_rank,
                                                  frequency_band, translation_cs)
                       VALUES ('00000000-0000-0000-0000-0000000000e1', 'en', 'dog', 'NOUN',
                               75, 100, 'pes')"""
                )
            )
        with pytest.raises(subprocess.CalledProcessError) as exc:
            alembic("downgrade", "0006")
        assert b"holds English rows" in exc.value.stderr
        async with engine.begin() as conn:  # still at head, English row intact
            lemma = await conn.scalar(text("SELECT lemma FROM lexicon_items WHERE language = 'en'"))
        assert lemma == "dog"
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM lexicon_items"))
        await engine.dispose()
        alembic("upgrade", "head")
