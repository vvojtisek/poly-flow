"""Word notes: a learner's own memory hook per word.

New table only. Downgrade drops it, which deletes the learners' notes.

Revision ID: 0020
Revises: 0019
"""

import sqlalchemy as sa

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "word_notes",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lexicon_item_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.String(length=280), nullable=False),
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
        sa.CheckConstraint("char_length(text) BETWEEN 1 AND 280", name=op.f("ck_word_notes_text")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_word_notes_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["lexicon_item_id"],
            ["lexicon_items.id"],
            name=op.f("fk_word_notes_lexicon_item_id_lexicon_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "lexicon_item_id", name=op.f("pk_word_notes")),
    )


def downgrade() -> None:
    op.drop_table("word_notes")
