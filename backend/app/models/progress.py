import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import ProgressStateType
from app.domain.enums import ProgressState


class UserWordProgress(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_word_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lexicon_item_id", name="uq_user_word_progress_user_item"),
        CheckConstraint(
            "phonetic_score IS NULL OR phonetic_score BETWEEN 0 AND 1", name="phonetic_range"
        ),
        CheckConstraint(
            "orthography_score IS NULL OR orthography_score BETWEEN 0 AND 1",
            name="orthography_range",
        ),
        # Decay sweep: rows per state ordered by staleness.
        Index("ix_user_word_progress_state_error_free", "state", "last_error_free_at"),
        Index("ix_user_word_progress_user_state", "user_id", "state"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    lexicon_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lexicon_items.id", ondelete="CASCADE"), nullable=False
    )

    state: Mapped[ProgressState] = mapped_column(
        ProgressStateType,
        default=ProgressState.NEW,
        server_default=ProgressState.NEW.value,
        nullable=False,
    )
    passive_known: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    active_known: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    # Rolling accuracies in [0, 1]; NULL = never measured (distinct from measured-as-zero).
    phonetic_score: Mapped[float | None] = mapped_column(Float)
    orthography_score: Mapped[float | None] = mapped_column(Float)

    correct_count: Mapped[int] = mapped_column(default=0, server_default=text("0"), nullable=False)
    error_count: Mapped[int] = mapped_column(default=0, server_default=text("0"), nullable=False)

    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Last review with no errors; decay triggers when this is > DECAY_AFTER_DAYS old.
    last_error_free_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_decay_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", back_populates="progress")
    item = relationship("LexiconItem", back_populates="progress")
