from sqlalchemy import CheckConstraint, Index, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import CefrLevelType, LanguageType
from app.domain.enums import CefrLevel, Language


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
        CheckConstraint("frequency_rank BETWEEN 1 AND 2500", name="rank_range"),
        Index("ix_lexicon_items_language_band", "language", "frequency_band"),
    )

    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    lemma: Mapped[str] = mapped_column(String(128), nullable=False)
    # Universal POS tag (NOUN, VERB, ...); empty string when unknown so the unique key holds.
    pos: Mapped[str] = mapped_column(String(16), default="", server_default="", nullable=False)
    frequency_rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # Denormalised milestone bound (100/500/1000/1500/2000/2500); set by the importer.
    frequency_band: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    translation_cs: Mapped[str] = mapped_column(String(255), nullable=False)
    ipa: Mapped[str | None] = mapped_column(String(128))
    cefr_level: Mapped[CefrLevel | None] = mapped_column(CefrLevelType)
    gender: Mapped[str | None] = mapped_column(String(8))  # der/die/das, m/f
    example_sentence: Mapped[str | None] = mapped_column(String(512))
    audio_path: Mapped[str | None] = mapped_column(String(255))

    progress = relationship("UserWordProgress", back_populates="item", cascade="all, delete-orphan")
