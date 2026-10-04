"""Frequency lemma reference lists (10,000 most frequent en_US lemmas)

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "frequency_lemmas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("lemma", sa.String(length=64), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("frequency_band", sa.Integer(), nullable=False),
        sa.Column("pos", sa.String(length=16), nullable=True),
        sa.Column(
            "content_flags",
            postgresql.ARRAY(sa.String(length=16)),
            server_default=sa.text("'{}'::varchar[]"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("license", sa.String(length=32), nullable=False),
        sa.Column("revision", sa.String(length=32), nullable=False),
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
        sa.CheckConstraint("rank >= 1", name=op.f("ck_frequency_lemmas_rank_positive")),
        sa.CheckConstraint(
            "lemma ~ '^[a-z]+(-[a-z]+)*$'", name=op.f("ck_frequency_lemmas_lemma_normalised")
        ),
        sa.CheckConstraint(
            "locale ~ '^[a-z]{2}_[A-Z]{2}$'", name=op.f("ck_frequency_lemmas_locale_format")
        ),
        sa.CheckConstraint(
            "content_flags <@ ARRAY['sexual', 'profanity', 'violence']::varchar[]",
            name=op.f("ck_frequency_lemmas_content_flags_known"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_frequency_lemmas")),
        sa.UniqueConstraint("locale", "lemma", name="uq_frequency_lemmas_locale_lemma"),
        sa.UniqueConstraint(
            "locale",
            "rank",
            name="uq_frequency_lemmas_locale_rank",
            deferrable=True,
            initially="DEFERRED",
        ),
    )


def downgrade() -> None:
    op.drop_table("frequency_lemmas")
