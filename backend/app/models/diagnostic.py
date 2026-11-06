"""CEFR placement diagnostic (rozřazovací test, part 2): sessions and the latest result.

Items come from the language's item bank file (`app.services.diagnostic.bank`), not from the
database: a session stores the asked item ids with the shown option order and the answers, so a
re-import of the bank never changes a running or finished test.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import CefrLevelType, LanguageType
from app.domain.enums import CefrLevel, Language


class DiagnosticSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "diagnostic_sessions"
    __table_args__ = (
        Index(
            "uq_diagnostic_sessions_one_active",
            "user_id",
            "language",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        CheckConstraint("status IN ('active', 'completed', 'abandoned')", name="status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="active", server_default="active", nullable=False
    )
    policy_version: Mapped[str] = mapped_column(String(16), nullable=False)
    bank_revision: Mapped[str] = mapped_column(String(32), nullable=False)
    prior_mean: Mapped[float] = mapped_column(Float, nullable=False)
    with_listening: Mapped[bool] = mapped_column(nullable=False)
    # [{"id", "options": [shown order], "choice": str | null, "correct": bool | null,
    #   "answered": bool}] in the order asked; the last entry may be pending.
    items: Mapped[list] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb"), nullable=False
    )
    result: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CefrPlacement(TimestampMixin, Base):
    """The latest CEFR diagnostic result per profile and language (a retake replaces it).

    `level` NULL = below the A1 items (a beginner). C1 stands for "B2+": above the B2 items,
    never reported as a C1 certificate.
    """

    __tablename__ = "cefr_placements"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, primary_key=True)
    level: Mapped[CefrLevel | None] = mapped_column(CefrLevelType)
    theta: Mapped[float] = mapped_column(Float, nullable=False)
    theta_sd: Mapped[float] = mapped_column(Float, nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("diagnostic_sessions.id", ondelete="SET NULL")
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(16), nullable=False)
