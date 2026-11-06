"""Personal mastery awards: ranks and achievements a profile reached, per language.

A row is written the first time the evidence supports it and never removed by decay (a rank once
reached is kept). `seen_at` NULL = not yet celebrated in the UI.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.types import LanguageType
from app.domain.enums import Language


class MasteryAward(TimestampMixin, Base):
    __tablename__ = "mastery_awards"
    __table_args__ = (CheckConstraint("kind IN ('rank', 'achievement')", name="kind"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    key: Mapped[str] = mapped_column(String(32), primary_key=True)  # rank number or achievement
    reached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
