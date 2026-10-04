"""Vocabulary level exams: exam session mode and level badges

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

LANGUAGE = postgresql.ENUM("de", "fr", "it", "en", name="language", create_type=False)
CEFR = postgresql.ENUM("A1", "A2", "B1", "B2", "C1", "C2", name="cefr_level", create_type=False)


def upgrade() -> None:
    # PostgreSQL >= 12 allows this inside the migration transaction. The new value cannot be
    # used before commit, so the check below compares the mode as text.
    op.execute("ALTER TYPE learning_session_mode ADD VALUE IF NOT EXISTS 'exam'")

    op.add_column("learning_sessions", sa.Column("exam_level", CEFR, nullable=True))
    op.create_check_constraint(
        op.f("ck_learning_sessions_exam_level"),
        "learning_sessions",
        "(mode::text = 'exam') = (exam_level IS NOT NULL)",
    )

    op.create_table(
        "level_badges",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("language", LANGUAGE, nullable=False),
        sa.Column("level", CEFR, nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("correct", sa.Integer(), nullable=False),
        sa.Column("asked", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.String(length=16), nullable=False),
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
            "level::text IN ('A1', 'A2', 'B1', 'B2')", name=op.f("ck_level_badges_level")
        ),
        sa.CheckConstraint("correct BETWEEN 0 AND asked", name=op.f("ck_level_badges_score")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_level_badges_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning_sessions.id"],
            name=op.f("fk_level_badges_session_id_learning_sessions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("user_id", "language", "level", name=op.f("pk_level_badges")),
    )


def downgrade() -> None:
    # Badges go with the feature. Exam sessions go too (their tasks with them); their learning
    # events and the progress they produced stay as check evidence.
    op.drop_table("level_badges")
    op.execute("DELETE FROM learning_sessions WHERE mode = 'exam'")
    op.drop_constraint(op.f("ck_learning_sessions_exam_level"), "learning_sessions", type_="check")
    op.drop_column("learning_sessions", "exam_level")

    # PostgreSQL cannot drop an enum value, so the type is rebuilt without it.
    op.execute("ALTER TABLE learning_sessions ALTER COLUMN mode DROP DEFAULT")
    op.execute("ALTER TYPE learning_session_mode RENAME TO learning_session_mode_old")
    op.execute("CREATE TYPE learning_session_mode AS ENUM ('learn', 'check', 'placement')")
    op.execute(
        "ALTER TABLE learning_sessions ALTER COLUMN mode TYPE learning_session_mode "
        "USING mode::text::learning_session_mode"
    )
    op.execute("ALTER TABLE learning_sessions ALTER COLUMN mode SET DEFAULT 'learn'")
    op.execute("DROP TYPE learning_session_mode_old")
