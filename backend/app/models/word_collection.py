"""Private, learner-curated groups of words already encountered in lessons."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import LanguageType
from app.domain.enums import Language


class WordCollection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "word_collections"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "language", "name", name="uq_word_collections_user_language_name"
        ),
        CheckConstraint("char_length(name) BETWEEN 1 AND 60", name="name"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)


class WordCollectionItem(TimestampMixin, Base):
    __tablename__ = "word_collection_items"

    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("word_collections.id", ondelete="CASCADE"), primary_key=True
    )
    lexicon_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lexicon_items.id", ondelete="CASCADE"), primary_key=True
    )
