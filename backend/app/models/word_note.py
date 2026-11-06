"""A learner's own memory hook for a word (oslí můstek): free text, private to the profile.

The text is the learner's, untrusted and never shown to anyone else; it is not logged.
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

MAX_NOTE = 280


class WordNote(TimestampMixin, Base):
    __tablename__ = "word_notes"
    __table_args__ = (CheckConstraint(f"char_length(text) BETWEEN 1 AND {MAX_NOTE}", name="text"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    lexicon_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lexicon_items.id", ondelete="CASCADE"), primary_key=True
    )
    text: Mapped[str] = mapped_column(String(MAX_NOTE), nullable=False)
