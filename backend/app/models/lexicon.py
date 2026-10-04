from sqlalchemy import CheckConstraint, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import CefrLevelType, LanguageType
from app.domain.enums import CefrLevel, ContentFlag, Language

_FLAG_VALUES = ", ".join(f"'{f.value}'" for f in ContentFlag)


class LexiconItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lexicon_items"
    __table_args__ = (
        UniqueConstraint("language", "lemma", "pos", name="uq_lexicon_items_language_lemma_pos"),
        # Deferred so re-imports that shift ranks only need consistency at commit.
        UniqueConstraint(
            "language",
            "frequency_rank",
            name="uq_lexicon_items_language_rank",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("frequency_rank >= 1", name="rank_positive"),
        CheckConstraint(
            f"content_flags <@ ARRAY[{_FLAG_VALUES}]::varchar[]", name="content_flags_known"
        ),
        Index("ix_lexicon_items_language_band", "language", "frequency_band"),
    )

    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    lemma: Mapped[str] = mapped_column(String(128), nullable=False)
    # Universal POS tag (NOUN, VERB, ...); empty string when unknown so the unique key holds.
    pos: Mapped[str] = mapped_column(String(16), default="", server_default="", nullable=False)
    # Open-ended: the curriculum ends at 5000, the voluntary extension continues past it.
    frequency_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    # Denormalised milestone (app.domain.progression.frequency_band); set by the importer.
    frequency_band: Mapped[int] = mapped_column(Integer, nullable=False)
    translation_cs: Mapped[str] = mapped_column(String(255), nullable=False)
    ipa: Mapped[str | None] = mapped_column(String(128))
    cefr_level: Mapped[CefrLevel | None] = mapped_column(CefrLevelType)
    gender: Mapped[str | None] = mapped_column(String(8))  # der/die/das, m/f
    example_sentence: Mapped[str | None] = mapped_column(String(512))
    audio_path: Mapped[str | None] = mapped_column(String(255))
    # Age-appropriate filter: child profiles never get an item with any flag (ContentFlag values).
    content_flags: Mapped[list[str]] = mapped_column(
        ARRAY(String(16)), default=list, server_default=text("'{}'::varchar[]"), nullable=False
    )
    # Provenance (plan P2): where the row came from, under which licence, which data revision.
    source: Mapped[str | None] = mapped_column(String(64))
    license: Mapped[str | None] = mapped_column(String(32))
    revision: Mapped[str | None] = mapped_column(String(32))

    progress = relationship("UserWordProgress", back_populates="item", cascade="all, delete-orphan")
