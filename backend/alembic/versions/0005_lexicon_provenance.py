"""lexicon provenance

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lexicon_items", sa.Column("source", sa.String(length=64), nullable=True))
    op.add_column("lexicon_items", sa.Column("license", sa.String(length=32), nullable=True))
    op.add_column("lexicon_items", sa.Column("revision", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("lexicon_items", "revision")
    op.drop_column("lexicon_items", "license")
    op.drop_column("lexicon_items", "source")
