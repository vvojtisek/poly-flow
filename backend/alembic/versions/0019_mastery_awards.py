"""Personal mastery awards (ranks and achievements per profile and language).

New table only. Downgrade drops it: awards are derived from learning evidence, which stays.

Revision ID: 0019
Revises: 0018
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

LANGUAGE = postgresql.ENUM("de", "fr", "it", "en", name="language", create_type=False)

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mastery_awards",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("language", LANGUAGE, nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("reached_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("kind IN ('rank', 'achievement')", name=op.f("ck_mastery_awards_kind")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_mastery_awards_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "language", "kind", "key", name=op.f("pk_mastery_awards")
        ),
    )


def downgrade() -> None:
    op.drop_table("mastery_awards")
