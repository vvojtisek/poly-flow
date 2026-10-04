"""Spoken answers: how an attempt was given and the transcript's confidence

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing events were all typed (or chosen); the default fills them without a rewrite.
    op.add_column(
        "learning_events",
        sa.Column("answer_mode", sa.String(8), server_default="typed", nullable=False),
    )
    op.add_column("learning_events", sa.Column("transcript_confidence", sa.Float(), nullable=True))
    op.create_check_constraint(
        op.f("ck_learning_events_answer_mode"),
        "learning_events",
        "answer_mode IN ('typed', 'spoken')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_learning_events_answer_mode"), "learning_events", type_="check")
    op.drop_column("learning_events", "transcript_confidence")
    op.drop_column("learning_events", "answer_mode")
