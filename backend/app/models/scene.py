import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import LanguageType
from app.domain.enums import Language


class Scene(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A short situation (dialogue) that introduces words in context before any practice."""

    __tablename__ = "scenes"
    __table_args__ = (
        UniqueConstraint("language", "slug", name="uq_scenes_language_slug"),
        Index("ix_scenes_language_position", "language", "position"),
    )

    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    # Curriculum order within the language: lessons walk scenes by ascending position.
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title_cs: Mapped[str] = mapped_column(String(128), nullable=False)
    # [{"speaker": "A", "text": "<target language>", "cs": "<Czech translation>"}, ...]
    lines: Mapped[list] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb"), nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(64))
    revision: Mapped[str | None] = mapped_column(String(32))

    words = relationship(
        "SceneWord",
        back_populates="scene",
        order_by="SceneWord.position",
        cascade="all, delete-orphan",
    )


class SceneWord(Base):
    """A word the scene introduces (taught in the lesson built from this scene)."""

    __tablename__ = "scene_words"
    __table_args__ = (Index("ix_scene_words_lexicon_item", "lexicon_item_id"),)

    scene_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"), primary_key=True
    )
    lexicon_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lexicon_items.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    scene = relationship("Scene", back_populates="words")
    item = relationship("LexiconItem")
