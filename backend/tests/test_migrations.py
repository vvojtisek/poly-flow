"""Upgrading a database that already holds learner data must not lose or alter it."""

import ast
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from tests.conftest import alembic

VERSIONS = Path(__file__).resolve().parent.parent / "alembic" / "versions"

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


def _revision_ids() -> dict[str, tuple[str, str | None]]:
    """file name -> (revision, down_revision), read without importing the migrations."""
    ids = {}
    for path in sorted(VERSIONS.glob("*.py")):
        values = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in ("revision", "down_revision")
        }
        ids[path.name] = (values["revision"], values["down_revision"])
    return ids


def test_migrations_form_one_linear_history():
    # Two branches that each add the next number merge cleanly in git but leave Alembic
    # with duplicate ids or two heads, and `alembic upgrade head` then refuses to run.
    ids = _revision_ids()
    revisions = [rev for rev, _ in ids.values()]
    duplicates = sorted({r for r in revisions if revisions.count(r) > 1})
    assert not duplicates, f"duplicate revision ids: {duplicates} in {sorted(ids)}"
    parents = {down for _, down in ids.values()}
    heads = sorted(set(revisions) - parents)
    assert len(heads) == 1, f"expected one head, found {heads}"


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


async def test_downgrade_below_0008_refuses_to_drop_english(migrated_db):
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
            alembic("downgrade", "0007")
        assert b"holds English rows" in exc.value.stderr
        async with engine.begin() as conn:  # still at head, English row intact
            lemma = await conn.scalar(text("SELECT lemma FROM lexicon_items WHERE language = 'en'"))
        assert lemma == "dog"
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM lexicon_items"))
        await engine.dispose()
        alembic("upgrade", "head")


async def test_downgrade_below_0010_keeps_lesson_progress(migrated_db):
    user, taught, queued = (
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-0000000000b1",
        "00000000-0000-0000-0000-0000000000b2",
    )
    engine = create_async_engine(migrated_db, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(f"INSERT INTO users (id, username, display_name) VALUES ('{user}', 'a', 'A')")
            )
            for n, lemma in ((1, "Haus"), (2, "Baum")):
                await conn.execute(
                    text(
                        f"""INSERT INTO lexicon_items (id, language, lemma, pos, frequency_rank,
                                                       frequency_band, translation_cs)
                            VALUES ('00000000-0000-0000-0000-0000000000a{n}', 'de', '{lemma}',
                                    'NOUN', {n}, 100, 'x{n}')"""
                    )
                )
            for pid, n, by in ((taught, 1, "lesson"), (queued, 2, "placement")):
                await conn.execute(
                    text(
                        f"""INSERT INTO user_word_progress (id, user_id, lexicon_item_id,
                                                            introduced_at, introduced_by,
                                                            next_review_at)
                            VALUES ('{pid}', '{user}', '00000000-0000-0000-0000-0000000000a{n}',
                                    now(), '{by}', now())"""
                    )
                )
            await conn.execute(
                text(
                    f"""INSERT INTO learning_sessions (id, user_id, language, mode, status,
                                                       policy_version, summary)
                        VALUES ('00000000-0000-0000-0000-0000000000c1', '{user}', 'de',
                                'placement', 'completed', 'v3', '{{}}')"""
                )
            )

        alembic("downgrade", "0009")
        async with engine.begin() as conn:
            introduced = dict(
                (
                    await conn.execute(
                        text("SELECT id::text, introduced_at FROM user_word_progress")
                    )
                ).all()
            )
            sessions = await conn.scalar(text("SELECT count(*) FROM learning_sessions"))
        assert introduced[taught] is not None  # a lesson-taught word stays checkable
        assert introduced[queued] is None  # never taught or checked: back to the lessons
        assert sessions == 0

        alembic("upgrade", "head")
        async with engine.begin() as conn:
            by = await conn.scalar(
                text(f"SELECT introduced_by FROM user_word_progress WHERE id = '{taught}'")
            )
        assert by == "lesson"
    finally:
        async with engine.begin() as conn:
            for table in ("learning_sessions", "user_word_progress", "lexicon_items", "users"):
                await conn.execute(text(f"DELETE FROM {table}"))
        await engine.dispose()
        alembic("upgrade", "head")
