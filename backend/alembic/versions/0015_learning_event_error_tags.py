"""Error tag on learning events (policy v4 mistake engine).

Nullable column; existing events keep NULL (recorded before tags existed).

Revision ID: 0015
Revises: 0014
"""

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("learning_events", sa.Column("error_tag", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("learning_events", "error_tag")
