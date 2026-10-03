"""learning sessions events and review schedule

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grammar_unlocks",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "language",
            postgresql.ENUM("de", "fr", "it", name="language", create_type=False),
            nullable=False,
        ),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=False),
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
            ["user_id"],
            ["users.id"],
            name=op.f("fk_grammar_unlocks_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "language", name=op.f("pk_grammar_unlocks")),
    )
    op.create_table(
        "learning_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "language",
            postgresql.ENUM("de", "fr", "it", name="language", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "completed", "abandoned", name="learning_session_status"),
            server_default="active",
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_learning_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_sessions")),
    )
    op.create_index(
        "uq_learning_sessions_one_active",
        "learning_sessions",
        ["user_id", "language"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "learning_tasks",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("lexicon_item_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "task_type", sa.Enum("recognition", "recall", name="learning_task_type"), nullable=False
        ),
        sa.Column("is_new_item", sa.Boolean(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "done", "revealed", name="learning_task_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("hint_level", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["lexicon_item_id"],
            ["lexicon_items.id"],
            name=op.f("fk_learning_tasks_lexicon_item_id_lexicon_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning_sessions.id"],
            name=op.f("fk_learning_tasks_session_id_learning_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_tasks")),
        sa.UniqueConstraint("session_id", "position", name="uq_learning_tasks_session_position"),
    )
    op.create_table(
        "learning_events",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lexicon_item_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column(
            "task_type", sa.Enum("recognition", "recall", name="learning_task_type"), nullable=False
        ),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("hint_used", sa.Boolean(), nullable=False),
        sa.Column("revealed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("counts_as_evidence", sa.Boolean(), nullable=False),
        sa.Column("orthography_score", sa.Float(), nullable=True),
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
            ["lexicon_item_id"],
            ["lexicon_items.id"],
            name=op.f("fk_learning_events_lexicon_item_id_lexicon_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning_sessions.id"],
            name=op.f("fk_learning_events_session_id_learning_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["learning_tasks.id"],
            name=op.f("fk_learning_events_task_id_learning_tasks"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_learning_events_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_events")),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_learning_events_idempotency"),
    )
    op.create_index(
        "ix_learning_events_user_item",
        "learning_events",
        ["user_id", "lexicon_item_id"],
        unique=False,
    )
    op.add_column(
        "user_word_progress", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "user_word_progress", sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "user_word_progress",
        sa.Column("review_streak", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "user_word_progress", sa.Column("known_since_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "user_word_progress", sa.Column("policy_version", sa.String(length=16), nullable=True)
    )
    op.create_index(
        "ix_user_word_progress_user_next_review",
        "user_word_progress",
        ["user_id", "next_review_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_word_progress_user_next_review", table_name="user_word_progress")
    op.drop_column("user_word_progress", "policy_version")
    op.drop_column("user_word_progress", "known_since_at")
    op.drop_column("user_word_progress", "review_streak")
    op.drop_column("user_word_progress", "next_review_at")
    op.drop_column("user_word_progress", "last_seen_at")
    op.drop_index("ix_learning_events_user_item", table_name="learning_events")
    op.drop_table("learning_events")
    op.drop_table("learning_tasks")
    op.drop_index(
        "uq_learning_sessions_one_active",
        table_name="learning_sessions",
        postgresql_where=sa.text("status = 'active'"),
    )
    op.drop_table("learning_sessions")
    op.drop_table("grammar_unlocks")
    for name in ("learning_task_status", "learning_task_type", "learning_session_status"):
        op.execute(f"DROP TYPE IF EXISTS {name}")
