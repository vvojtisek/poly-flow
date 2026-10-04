"""Placement test: session mode, per-language placement, how a word was introduced

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

LANGUAGE = postgresql.ENUM("de", "fr", "it", "en", name="language", create_type=False)


def upgrade() -> None:
    # PostgreSQL >= 12 allows this inside the migration transaction; nothing here uses it.
    op.execute("ALTER TYPE learning_session_mode ADD VALUE IF NOT EXISTS 'placement'")

    op.add_column("user_word_progress", sa.Column("introduced_by", sa.String(16), nullable=True))
    # Every word introduced so far came from a lesson (or v1 practice, which taught it).
    op.execute(
        "UPDATE user_word_progress SET introduced_by = 'lesson' WHERE introduced_at IS NOT NULL"
    )
    op.create_check_constraint(
        op.f("ck_user_word_progress_introduced_by"),
        "user_word_progress",
        "introduced_by IS NULL OR introduced_by IN ('lesson', 'placement')",
    )

    op.create_table(
        "language_placements",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("language", LANGUAGE, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.Column("level_low", sa.Integer(), nullable=True),
        sa.Column("level_high", sa.Integer(), nullable=True),
        sa.Column("ceiling", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_version", sa.String(length=16), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('placed', 'skipped')", name=op.f("ck_language_placements_status")
        ),
        sa.CheckConstraint(
            "(status = 'placed') = (level IS NOT NULL)",
            name=op.f("ck_language_placements_level_when_placed"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_language_placements_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning_sessions.id"],
            name=op.f("fk_language_placements_session_id_learning_sessions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("user_id", "language", name=op.f("pk_language_placements")),
    )


def downgrade() -> None:
    op.drop_table("language_placements")
    # Words a placement queued for confirmation were never taught or checked: without
    # `introduced_by` nothing could send them back to the lessons, so un-introduce them.
    # Words with check results keep them.
    op.execute(
        "UPDATE user_word_progress SET introduced_at = NULL, next_review_at = NULL "
        "WHERE introduced_by = 'placement' AND last_reviewed_at IS NULL"
    )
    op.drop_constraint(
        op.f("ck_user_word_progress_introduced_by"), "user_word_progress", type_="check"
    )
    op.drop_column("user_word_progress", "introduced_by")

    # PostgreSQL cannot drop an enum value, so the type is rebuilt without it. Placement
    # sessions go (their tasks with them); their learning events stay as evidence.
    op.execute("DELETE FROM learning_sessions WHERE mode = 'placement'")
    op.execute("ALTER TABLE learning_sessions ALTER COLUMN mode DROP DEFAULT")
    op.execute("ALTER TYPE learning_session_mode RENAME TO learning_session_mode_old")
    op.execute("CREATE TYPE learning_session_mode AS ENUM ('learn', 'check')")
    op.execute(
        "ALTER TABLE learning_sessions ALTER COLUMN mode TYPE learning_session_mode "
        "USING mode::text::learning_session_mode"
    )
    op.execute("ALTER TABLE learning_sessions ALTER COLUMN mode SET DEFAULT 'learn'")
    op.execute("DROP TYPE learning_session_mode_old")
