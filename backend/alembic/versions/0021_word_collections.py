"""Learner-owned vocabulary collections.

Revision ID: 0021
Revises: 0020
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "word_collections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "language",
            postgresql.ENUM("de", "fr", "it", "en", name="language", create_type=False),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=60), nullable=False),
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
            "char_length(name) BETWEEN 1 AND 60", name=op.f("ck_word_collections_name")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_word_collections_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_word_collections")),
        sa.UniqueConstraint(
            "user_id", "language", "name", name=op.f("uq_word_collections_user_language_name")
        ),
    )
    op.create_index(
        op.f("ix_word_collections_user_id"), "word_collections", ["user_id"], unique=False
    )
    op.create_table(
        "word_collection_items",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("lexicon_item_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["word_collections.id"],
            name=op.f("fk_word_collection_items_collection_id_word_collections"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lexicon_item_id"],
            ["lexicon_items.id"],
            name=op.f("fk_word_collection_items_lexicon_item_id_lexicon_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "collection_id", "lexicon_item_id", name=op.f("pk_word_collection_items")
        ),
    )


def downgrade() -> None:
    op.drop_table("word_collection_items")
    op.drop_index(op.f("ix_word_collections_user_id"), table_name="word_collections")
    op.drop_table("word_collections")
