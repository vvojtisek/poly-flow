"""Tutor explanations with provenance (curriculum or a named local model).

New table only.

Revision ID: 0016
Revises: 0015
"""

import sqlalchemy as sa

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tutor_explanations",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("ref_id", sa.String(length=64), nullable=False),
        sa.Column("question_hash", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint("kind IN ('word', 'grammar')", name=op.f("ck_tutor_explanations_kind")),
        sa.CheckConstraint(
            "source IN ('curriculum', 'model')", name=op.f("ck_tutor_explanations_source")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_tutor_explanations_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tutor_explanations")),
        sa.UniqueConstraint(
            "user_id", "kind", "ref_id", "question_hash", name="uq_tutor_explanations"
        ),
    )


def downgrade() -> None:
    op.drop_table("tutor_explanations")
