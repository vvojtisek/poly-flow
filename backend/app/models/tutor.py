import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TutorExplanation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An explanation the tutor gave, with its origin (curriculum text or a named model).

    Stored so a repeated request returns the same text and so model output can be traced.
    The learner's own question is not kept, only its hash (to tell questions apart).
    """

    __tablename__ = "tutor_explanations"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "kind", "ref_id", "question_hash", name="uq_tutor_explanations"
        ),
        CheckConstraint("kind IN ('word', 'grammar')", name="kind"),
        CheckConstraint("source IN ('curriculum', 'model')", name="source"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    ref_id: Mapped[str] = mapped_column(String(64), nullable=False)  # task or session item id
    question_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(128))
    model: Mapped[str | None] = mapped_column(String(128))
    text: Mapped[str] = mapped_column(Text, nullable=False)
