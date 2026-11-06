"""CEFR placement diagnostic: sessions, latest result, and placement-queued grammar units.

New tables plus one nullable column; existing rows keep NULL `studied_by` (= unknown source,
treated as a lesson). Downgrade drops the new data: placement-queued grammar units that no
check has confirmed go back to "not studied", so no unit stays checkable without a lesson.

Revision ID: 0018
Revises: 0017
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

LANGUAGE = postgresql.ENUM("de", "fr", "it", "en", name="language", create_type=False)
CEFR = postgresql.ENUM("A1", "A2", "B1", "B2", "C1", "C2", name="cefr_level", create_type=False)

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "diagnostic_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("language", LANGUAGE, nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("policy_version", sa.String(length=16), nullable=False),
        sa.Column("bank_revision", sa.String(length=32), nullable=False),
        sa.Column("prior_mean", sa.Float(), nullable=False),
        sa.Column("with_listening", sa.Boolean(), nullable=False),
        sa.Column(
            "items",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'abandoned')",
            name=op.f("ck_diagnostic_sessions_status"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_diagnostic_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnostic_sessions")),
    )
    op.create_index(
        "uq_diagnostic_sessions_one_active",
        "diagnostic_sessions",
        ["user_id", "language"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "cefr_placements",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("language", LANGUAGE, nullable=False),
        sa.Column("level", CEFR, nullable=True),
        sa.Column("theta", sa.Float(), nullable=False),
        sa.Column("theta_sd", sa.Float(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_version", sa.String(length=16), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["diagnostic_sessions.id"],
            name=op.f("fk_cefr_placements_session_id_diagnostic_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_cefr_placements_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "language", name=op.f("pk_cefr_placements")),
    )
    op.add_column(
        "user_grammar_progress", sa.Column("studied_by", sa.String(length=16), nullable=True)
    )


def downgrade() -> None:
    op.execute(
        "UPDATE user_grammar_progress SET studied_at = NULL, next_review_at = NULL, "
        "state = 'NEW' WHERE studied_by = 'placement' AND last_reviewed_at IS NULL"
    )
    op.drop_column("user_grammar_progress", "studied_by")
    op.drop_table("cefr_placements")
    op.drop_index("uq_diagnostic_sessions_one_active", table_name="diagnostic_sessions")
    op.drop_table("diagnostic_sessions")
