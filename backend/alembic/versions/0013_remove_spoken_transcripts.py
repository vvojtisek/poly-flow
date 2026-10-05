"""Remove raw spoken transcripts from learning events.

Revision ID: 0013
Revises: 0012
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Spoken transcripts are grading input, not learner progress. The migration is deliberately
    # one-way: restoring the removed child/learner text would defeat the privacy fix.
    op.execute(
        """
        UPDATE learning_events
        SET answer = '[spoken]', result = result - 'heard'
        WHERE answer_mode = 'spoken'
        """
    )


def downgrade() -> None:
    # The removed transcripts are intentionally not recoverable.
    pass
