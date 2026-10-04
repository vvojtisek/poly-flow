"""learn and check modes, scenes

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

LANGUAGE = postgresql.ENUM("de", "fr", "it", name="language", create_type=False)
MODE = postgresql.ENUM("learn", "check", name="learning_session_mode")


def upgrade() -> None:
    op.create_table(
        "scenes",
        sa.Column("language", LANGUAGE, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title_cs", sa.String(length=128), nullable=False),
        sa.Column(
            "lines",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("revision", sa.String(length=32), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenes")),
        sa.UniqueConstraint("language", "slug", name="uq_scenes_language_slug"),
    )
    op.create_index("ix_scenes_language_position", "scenes", ["language", "position"])
    op.create_table(
        "scene_words",
        sa.Column("scene_id", sa.Uuid(), nullable=False),
        sa.Column("lexicon_item_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["lexicon_item_id"],
            ["lexicon_items.id"],
            name=op.f("fk_scene_words_lexicon_item_id_lexicon_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scene_id"],
            ["scenes.id"],
            name=op.f("fk_scene_words_scene_id_scenes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("scene_id", "lexicon_item_id", name=op.f("pk_scene_words")),
    )
    op.create_index("ix_scene_words_lexicon_item", "scene_words", ["lexicon_item_id"])

    MODE.create(op.get_bind())
    op.add_column(
        "learning_sessions",
        sa.Column("mode", MODE, server_default="learn", nullable=False),
    )
    op.add_column("learning_sessions", sa.Column("scene_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_learning_sessions_scene_id_scenes"),
        "learning_sessions",
        "scenes",
        ["scene_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_index("uq_learning_sessions_one_active", table_name="learning_sessions")
    op.create_index(
        "uq_learning_sessions_one_active",
        "learning_sessions",
        ["user_id", "language", "mode"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.add_column(
        "user_word_progress", sa.Column("introduced_at", sa.DateTime(timezone=True), nullable=True)
    )
    # Policy v1 practised every word it showed; keep those words checkable.
    op.execute(
        "UPDATE user_word_progress SET introduced_at = COALESCE(first_seen_at, created_at) "
        "WHERE state <> 'NEW'"
    )


def downgrade() -> None:
    op.drop_column("user_word_progress", "introduced_at")
    # v1 allows one open session per profile and language: close the open checks first.
    op.execute(
        "UPDATE learning_sessions SET status = 'abandoned' "
        "WHERE status = 'active' AND mode = 'check'"
    )
    op.drop_index("uq_learning_sessions_one_active", table_name="learning_sessions")
    op.create_index(
        "uq_learning_sessions_one_active",
        "learning_sessions",
        ["user_id", "language"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.drop_constraint(
        op.f("fk_learning_sessions_scene_id_scenes"), "learning_sessions", type_="foreignkey"
    )
    op.drop_column("learning_sessions", "scene_id")
    op.drop_column("learning_sessions", "mode")
    MODE.drop(op.get_bind())
    op.drop_index("ix_scene_words_lexicon_item", table_name="scene_words")
    op.drop_table("scene_words")
    op.drop_index("ix_scenes_language_position", table_name="scenes")
    op.drop_table("scenes")
