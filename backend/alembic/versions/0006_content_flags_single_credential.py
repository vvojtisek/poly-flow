"""lexicon content flags, one credential per profile

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lexicon_items",
        sa.Column(
            "content_flags",
            postgresql.ARRAY(sa.String(length=16)),
            server_default=sa.text("'{}'::varchar[]"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_lexicon_items_content_flags_known"),
        "lexicon_items",
        "content_flags <@ ARRAY['sexual', 'profanity', 'violence']::varchar[]",
    )
    # Before 0006 credentials were tied to is_child, so no row holds both.
    op.create_check_constraint(
        op.f("ck_users_single_credential"),
        "users",
        "password_hash IS NULL OR pin_hash IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_users_single_credential"), "users", type_="check")
    op.drop_constraint(op.f("ck_lexicon_items_content_flags_known"), "lexicon_items", type_="check")
    op.drop_column("lexicon_items", "content_flags")
