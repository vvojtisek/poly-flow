"""Separate lesson objective from discovery summary.

Revision ID: 0022
Revises: 0021
"""

import sqlalchemy as sa

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("grammar_units", sa.Column("objective", sa.String(length=400), nullable=True))
    op.execute("UPDATE grammar_units SET objective = summary")
    op.alter_column("grammar_units", "objective", nullable=False)


def downgrade() -> None:
    op.drop_column("grammar_units", "objective")
