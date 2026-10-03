"""Open-ended lexicon rank: curriculum to 5000 plus voluntary extension.

Drops the 1..2500 rank cap and widens rank/band to INTEGER.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_lexicon_items_rank_range"), "lexicon_items", type_="check")
    op.alter_column(
        "lexicon_items", "frequency_rank", type_=sa.Integer(), existing_type=sa.SmallInteger()
    )
    op.alter_column(
        "lexicon_items", "frequency_band", type_=sa.Integer(), existing_type=sa.SmallInteger()
    )
    op.create_check_constraint(
        op.f("ck_lexicon_items_rank_positive"), "lexicon_items", "frequency_rank >= 1"
    )


def downgrade() -> None:
    # Fails if extension items (rank > 2500) exist; delete them first.
    op.drop_constraint(op.f("ck_lexicon_items_rank_positive"), "lexicon_items", type_="check")
    op.alter_column(
        "lexicon_items", "frequency_band", type_=sa.SmallInteger(), existing_type=sa.Integer()
    )
    op.alter_column(
        "lexicon_items", "frequency_rank", type_=sa.SmallInteger(), existing_type=sa.Integer()
    )
    op.create_check_constraint(
        op.f("ck_lexicon_items_rank_range"), "lexicon_items", "frequency_rank BETWEEN 1 AND 2500"
    )
