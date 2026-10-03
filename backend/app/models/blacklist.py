from sqlalchemy import Boolean, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import BlacklistCategoryType, BlacklistPatternTypeType, LanguageType
from app.domain.enums import BlacklistCategory, BlacklistPatternType, Language


class ContentBlacklistEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Patterns that reject generated/scraped content for `is_child` profiles."""

    __tablename__ = "content_blacklist"
    __table_args__ = (
        # NULLS NOT DISTINCT: language-agnostic (NULL) patterns must also be unique.
        UniqueConstraint(
            "language",
            "pattern_type",
            "pattern",
            name="uq_content_blacklist_pattern",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_content_blacklist_active_language", "is_active", "language"),
    )

    # NULL = applies to every language (e.g. language-neutral regexes).
    language: Mapped[Language | None] = mapped_column(LanguageType)
    pattern_type: Mapped[BlacklistPatternType] = mapped_column(
        BlacklistPatternTypeType, nullable=False
    )
    pattern: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[BlacklistCategory] = mapped_column(BlacklistCategoryType, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255))
