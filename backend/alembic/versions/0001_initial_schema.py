"""initial schema

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

ENUM_TYPES = (
    "language",
    "user_role",
    "cefr_level",
    "progress_state",
    "blacklist_pattern_type",
    "blacklist_category",
    "story_source",
    "story_status",
)


def upgrade() -> None:
    op.create_table(
        "content_blacklist",
        sa.Column("language", sa.Enum("de", "fr", "it", name="language"), nullable=True),
        sa.Column(
            "pattern_type",
            sa.Enum("keyword", "regex", name="blacklist_pattern_type"),
            nullable=False,
        ),
        sa.Column("pattern", sa.String(length=512), nullable=False),
        sa.Column(
            "category",
            sa.Enum("violence", "adult", "politics", "other", name="blacklist_category"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_blacklist")),
        sa.UniqueConstraint(
            "language",
            "pattern_type",
            "pattern",
            name="uq_content_blacklist_pattern",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        "ix_content_blacklist_active_language",
        "content_blacklist",
        ["is_active", "language"],
        unique=False,
    )
    op.create_table(
        "lexicon_items",
        sa.Column("language", sa.Enum("de", "fr", "it", name="language"), nullable=False),
        sa.Column("lemma", sa.String(length=128), nullable=False),
        sa.Column("pos", sa.String(length=16), server_default="", nullable=False),
        sa.Column("frequency_rank", sa.SmallInteger(), nullable=False),
        sa.Column("frequency_band", sa.SmallInteger(), nullable=False),
        sa.Column("translation_cs", sa.String(length=255), nullable=False),
        sa.Column("ipa", sa.String(length=128), nullable=True),
        sa.Column(
            "cefr_level",
            sa.Enum("A1", "A2", "B1", "B2", "C1", "C2", name="cefr_level"),
            nullable=True,
        ),
        sa.Column("gender", sa.String(length=8), nullable=True),
        sa.Column("example_sentence", sa.String(length=512), nullable=True),
        sa.Column("audio_path", sa.String(length=255), nullable=True),
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
        sa.CheckConstraint(
            "frequency_rank BETWEEN 1 AND 2500", name=op.f("ck_lexicon_items_rank_range")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lexicon_items")),
        sa.UniqueConstraint(
            "language",
            "frequency_rank",
            name="uq_lexicon_items_language_rank",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.UniqueConstraint("language", "lemma", "pos", name="uq_lexicon_items_language_lemma_pos"),
    )
    op.create_index(
        "ix_lexicon_items_language_band",
        "lexicon_items",
        ["language", "frequency_band"],
        unique=False,
    )
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "role",
            sa.Enum("admin", "learner", name="user_role"),
            server_default="learner",
            nullable=False,
        ),
        sa.Column("is_child", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ui_locale", sa.String(length=8), server_default="cs-CZ", nullable=False),
        sa.Column(
            "active_language",
            sa.Enum("de", "fr", "it", name="language"),
            server_default="de",
            nullable=False,
        ),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("xp", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("coins", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("streak_current", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("streak_longest", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("streak_last_active_on", sa.Date(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )
    op.create_table(
        "daily_stories",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("language", sa.Enum("de", "fr", "it", name="language"), nullable=False),
        sa.Column("story_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "generated", "rejected", "failed", name="story_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "source_type",
            sa.Enum("rss_news", "fairy_tale", "myth", name="story_source"),
            nullable=False,
        ),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("source_title", sa.String(length=512), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column(
            "comprehension_questions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "new_item_ids",
            postgresql.ARRAY(sa.UUID()),
            server_default=sa.text("'{}'::uuid[]"),
            nullable=False,
        ),
        sa.Column("unknown_ratio", sa.Float(), nullable=True),
        sa.Column("safety_checked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("llm_provider", sa.String(length=32), nullable=True),
        sa.Column("llm_model", sa.String(length=64), nullable=True),
        sa.Column("audio_path", sa.String(length=255), nullable=True),
        sa.Column(
            "generation_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_daily_stories_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_daily_stories")),
        sa.UniqueConstraint(
            "user_id", "language", "story_date", name="uq_daily_stories_user_lang_date"
        ),
    )
    op.create_index(
        "ix_daily_stories_user_date", "daily_stories", ["user_id", "story_date"], unique=False
    )
    op.create_table(
        "user_word_progress",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lexicon_item_id", sa.Uuid(), nullable=False),
        sa.Column(
            "state",
            sa.Enum("NEW", "LEARNING", "MASTERED", name="progress_state"),
            server_default="NEW",
            nullable=False,
        ),
        sa.Column("passive_known", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("active_known", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("phonetic_score", sa.Float(), nullable=True),
        sa.Column("orthography_score", sa.Float(), nullable=True),
        sa.Column("correct_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_free_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_decay_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "orthography_score IS NULL OR orthography_score BETWEEN 0 AND 1",
            name=op.f("ck_user_word_progress_orthography_range"),
        ),
        sa.CheckConstraint(
            "phonetic_score IS NULL OR phonetic_score BETWEEN 0 AND 1",
            name=op.f("ck_user_word_progress_phonetic_range"),
        ),
        sa.ForeignKeyConstraint(
            ["lexicon_item_id"],
            ["lexicon_items.id"],
            name=op.f("fk_user_word_progress_lexicon_item_id_lexicon_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_word_progress_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_word_progress")),
        sa.UniqueConstraint("user_id", "lexicon_item_id", name="uq_user_word_progress_user_item"),
    )
    op.create_index(
        "ix_user_word_progress_state_error_free",
        "user_word_progress",
        ["state", "last_error_free_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_word_progress_user_state", "user_word_progress", ["user_id", "state"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_user_word_progress_user_state", table_name="user_word_progress")
    op.drop_index("ix_user_word_progress_state_error_free", table_name="user_word_progress")
    op.drop_table("user_word_progress")
    op.drop_index("ix_daily_stories_user_date", table_name="daily_stories")
    op.drop_table("daily_stories")
    op.drop_table("users")
    op.drop_index("ix_lexicon_items_language_band", table_name="lexicon_items")
    op.drop_table("lexicon_items")
    op.drop_index("ix_content_blacklist_active_language", table_name="content_blacklist")
    op.drop_table("content_blacklist")
    for name in ENUM_TYPES:
        op.execute(f"DROP TYPE IF EXISTS {name}")
