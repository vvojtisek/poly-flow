"""Grammar skill tree: units, exercises, sessions, attempts and per-unit progress.

New tables only; existing data is untouched.

Revision ID: 0014
Revises: 0013
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

LANGUAGE = postgresql.ENUM("de", "fr", "it", "en", name="language", create_type=False)
CEFR = postgresql.ENUM("A1", "A2", "B1", "B2", "C1", "C2", name="cefr_level", create_type=False)
STATE = postgresql.ENUM("NEW", "LEARNING", "MASTERED", name="progress_state", create_type=False)

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grammar_units",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("language", LANGUAGE, nullable=False),
        sa.Column("level", CEFR, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.String(length=400), nullable=False),
        sa.Column("notes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("examples", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("license", sa.String(length=32), nullable=False),
        sa.Column("revision", sa.String(length=32), nullable=False),
        sa.Column("review_status", sa.String(length=16), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            "review_status IN ('unreviewed', 'reviewed')",
            name=op.f("ck_grammar_units_review_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grammar_units")),
        sa.UniqueConstraint("language", "position", name="uq_grammar_units_language_position"),
    )
    op.create_table(
        "grammar_exercises",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("unit_id", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explain", sa.Text(), nullable=False),
        sa.Column(
            "content_flags",
            postgresql.ARRAY(sa.String(length=16)),
            server_default=sa.text("'{}'::varchar[]"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            "content_flags <@ ARRAY['sexual', 'profanity', 'violence']::varchar[]",
            name=op.f("ck_grammar_exercises_content_flags_known"),
        ),
        sa.CheckConstraint(
            "kind IN ('choice', 'gap', 'order', 'translate')",
            name=op.f("ck_grammar_exercises_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["grammar_units.id"],
            name=op.f("fk_grammar_exercises_unit_id_grammar_units"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grammar_exercises")),
        sa.UniqueConstraint("unit_id", "position", name="uq_grammar_exercises_unit_position"),
    )
    op.create_table(
        "grammar_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("language", LANGUAGE, nullable=False),
        sa.Column("mode", sa.String(length=8), nullable=False),
        sa.Column("unit_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("policy_version", sa.String(length=16), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "(mode = 'learn') = (unit_id IS NOT NULL)",
            name=op.f("ck_grammar_sessions_learn_has_unit"),
        ),
        sa.CheckConstraint("mode IN ('learn', 'check')", name=op.f("ck_grammar_sessions_mode")),
        sa.CheckConstraint(
            "status IN ('active', 'completed')", name=op.f("ck_grammar_sessions_status")
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["grammar_units.id"],
            name=op.f("fk_grammar_sessions_unit_id_grammar_units"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_grammar_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grammar_sessions")),
    )
    op.create_index(
        "uq_grammar_sessions_one_active",
        "grammar_sessions",
        ["user_id", "language", "mode"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "user_grammar_progress",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("unit_id", sa.String(length=64), nullable=False),
        sa.Column("state", STATE, server_default="NEW", nullable=False),
        sa.Column("studied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correct_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("review_streak", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_free_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_decay_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("known_since_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["grammar_units.id"],
            name=op.f("fk_user_grammar_progress_unit_id_grammar_units"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_grammar_progress_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "unit_id", name=op.f("pk_user_grammar_progress")),
    )
    op.create_index(
        "ix_user_grammar_progress_user_next_review",
        "user_grammar_progress",
        ["user_id", "next_review_at"],
        unique=False,
    )
    op.create_table(
        "grammar_session_items",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_remediation", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("first_try_correct", sa.Boolean(), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('pending', 'done', 'revealed')",
            name=op.f("ck_grammar_session_items_status"),
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["grammar_exercises.id"],
            name=op.f("fk_grammar_session_items_exercise_id_grammar_exercises"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["grammar_sessions.id"],
            name=op.f("fk_grammar_session_items_session_id_grammar_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grammar_session_items")),
        sa.UniqueConstraint("session_id", "position", name="uq_grammar_session_items_position"),
    )
    op.create_table(
        "grammar_attempts",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.String(length=64), nullable=False),
        sa.Column("unit_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column("mode", sa.String(length=8), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("answer", sa.String(length=500), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("error_tag", sa.String(length=32), nullable=True),
        sa.Column("revealed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("counts_as_evidence", sa.Boolean(), nullable=False),
        sa.Column("policy_version", sa.String(length=16), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["grammar_exercises.id"],
            name=op.f("fk_grammar_attempts_exercise_id_grammar_exercises"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["grammar_session_items.id"],
            name=op.f("fk_grammar_attempts_item_id_grammar_session_items"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["grammar_sessions.id"],
            name=op.f("fk_grammar_attempts_session_id_grammar_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["grammar_units.id"],
            name=op.f("fk_grammar_attempts_unit_id_grammar_units"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_grammar_attempts_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grammar_attempts")),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_grammar_attempts_idempotency"),
    )
    op.create_index(
        "ix_grammar_attempts_user_time",
        "grammar_attempts",
        ["user_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_grammar_attempts_user_unit", "grammar_attempts", ["user_id", "unit_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_grammar_attempts_user_unit", table_name="grammar_attempts")
    op.drop_index("ix_grammar_attempts_user_time", table_name="grammar_attempts")
    op.drop_table("grammar_attempts")
    op.drop_table("grammar_session_items")
    op.drop_index("ix_user_grammar_progress_user_next_review", table_name="user_grammar_progress")
    op.drop_table("user_grammar_progress")
    op.drop_index(
        "uq_grammar_sessions_one_active",
        table_name="grammar_sessions",
        postgresql_where=sa.text("status = 'active'"),
    )
    op.drop_table("grammar_sessions")
    op.drop_table("grammar_exercises")
    op.drop_table("grammar_units")
