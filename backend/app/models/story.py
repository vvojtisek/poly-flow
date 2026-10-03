import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import LanguageType, StorySourceType, StoryStatusType
from app.domain.enums import Language, StorySource, StoryStatus


class DailyStory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_stories"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "language", "story_date", name="uq_daily_stories_user_lang_date"
        ),
        Index("ix_daily_stories_user_date", "user_id", "story_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    story_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[StoryStatus] = mapped_column(
        StoryStatusType,
        default=StoryStatus.PENDING,
        server_default=StoryStatus.PENDING.value,
        nullable=False,
    )

    source_type: Mapped[StorySource] = mapped_column(StorySourceType, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1024))
    source_title: Mapped[str | None] = mapped_column(String(512))

    title: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text)
    # [{"question": str, "options": [str], "answer_index": int}] -- schema owned by the rewriter.
    comprehension_questions: Mapped[list] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb"), nullable=False
    )
    new_item_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, server_default=text("'{}'::uuid[]"), nullable=False
    )
    # Fraction of tokens intentionally outside the learner's known set (target 0.02-0.05).
    unknown_ratio: Mapped[float | None] = mapped_column(Float)
    # True once the child-safety guard ran (only meaningful for is_child users).
    safety_checked: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    llm_provider: Mapped[str | None] = mapped_column(String(32))
    llm_model: Mapped[str | None] = mapped_column(String(64))
    audio_path: Mapped[str | None] = mapped_column(String(255))
    generation_meta: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )

    user = relationship("User", back_populates="stories")
