"""Stories written by the local model from the learner's words (`story_source` 'generated').

Revision ID: 0017
Revises: 0016
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL >= 12 allows this inside the migration transaction.
    op.execute("ALTER TYPE story_source ADD VALUE IF NOT EXISTS 'generated'")


def downgrade() -> None:
    # PostgreSQL cannot drop an enum value, so the type is rebuilt without it. Generated
    # stories are derived reading texts (no learner progress depends on them): they are
    # removed rather than relabelled as another source.
    op.execute("DELETE FROM daily_stories WHERE source_type = 'generated'")
    op.execute("ALTER TYPE story_source RENAME TO story_source_with_generated")
    op.execute("CREATE TYPE story_source AS ENUM ('rss_news', 'fairy_tale', 'myth')")
    op.execute(
        "ALTER TABLE daily_stories ALTER COLUMN source_type TYPE story_source "
        "USING source_type::text::story_source"
    )
    op.execute("DROP TYPE story_source_with_generated")
