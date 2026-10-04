"""English as a fourth learning language

Revision ID: 0007
Revises: 0006
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

# Every column of the `language` enum type.
COLUMNS = (
    ("users", "active_language"),
    ("lexicon_items", "language"),
    ("content_blacklist", "language"),
    ("daily_stories", "language"),
    ("learning_sessions", "language"),
    ("grammar_unlocks", "language"),
)


def upgrade() -> None:
    # PostgreSQL >= 12 allows this inside the migration transaction; the new value is
    # usable once it commits.
    op.execute("ALTER TYPE language ADD VALUE IF NOT EXISTS 'en'")


def downgrade() -> None:
    # PostgreSQL cannot drop an enum value, so the type is rebuilt without it. Refuse
    # rather than delete English data (learner progress hangs off lexicon_items).
    bind = op.get_bind()
    for table, column in COLUMNS:
        found = bind.exec_driver_sql(f"SELECT 1 FROM {table} WHERE {column} = 'en' LIMIT 1").first()
        if found:
            raise RuntimeError(
                f"cannot downgrade below 0007: {table}.{column} holds English rows; "
                "remove English data deliberately first"
            )
    op.execute("ALTER TABLE users ALTER COLUMN active_language DROP DEFAULT")
    op.execute("ALTER TYPE language RENAME TO language_with_en")
    op.execute("CREATE TYPE language AS ENUM ('de', 'fr', 'it')")
    for table, column in COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE language "
            f"USING {column}::text::language"
        )
    op.execute("ALTER TABLE users ALTER COLUMN active_language SET DEFAULT 'de'")
    op.execute("DROP TYPE language_with_en")
