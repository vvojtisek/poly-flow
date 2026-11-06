"""Grammar skill tree (plan P5): content, sessions and per-rule progress.

Content (units, exercises) is seeded from `data/grammar/*.json`; ids are the pack's slugs, so a
re-import updates rows in place and never touches learner progress.

Learning and testing stay separate, as for words: a grammar lesson (learn) shows the unit's
notes and practises its exercises with retries and explanations; a grammar check is one
attempt per exercise and the only evidence that moves a rule's review schedule.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import CefrLevelType, LanguageType, ProgressStateType
from app.domain.enums import CefrLevel, ContentFlag, Language, ProgressState

_FLAG_VALUES = ", ".join(f"'{f.value}'" for f in ContentFlag)
_KINDS = "'choice', 'gap', 'order', 'translate'"


class GrammarUnit(TimestampMixin, Base):
    __tablename__ = "grammar_units"
    __table_args__ = (
        UniqueConstraint("language", "position", name="uq_grammar_units_language_position"),
        CheckConstraint("review_status IN ('unreviewed', 'reviewed')", name="review_status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    level: Mapped[CefrLevel] = mapped_column(CefrLevelType, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(String(400), nullable=False)
    objective: Mapped[str] = mapped_column(String(400), nullable=False)
    # [{"heading", "text", "table"?}], [{"text", "cs"}]: Czech explanation shown in the lesson.
    notes: Mapped[list] = mapped_column(JSONB, nullable=False)
    examples: Mapped[list] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    license: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[str] = mapped_column(String(32), nullable=False)
    review_status: Mapped[str] = mapped_column(String(16), nullable=False)
    # False: removed from the pack; kept so progress and attempts stay readable.
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    exercises = relationship(
        "GrammarExercise", back_populates="unit", order_by="GrammarExercise.position"
    )


class GrammarExercise(TimestampMixin, Base):
    __tablename__ = "grammar_exercises"
    __table_args__ = (
        UniqueConstraint("unit_id", "position", name="uq_grammar_exercises_unit_position"),
        CheckConstraint(f"kind IN ({_KINDS})", name="kind"),
        CheckConstraint(
            f"content_flags <@ ARRAY[{_FLAG_VALUES}]::varchar[]", name="content_flags_known"
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    unit_id: Mapped[str] = mapped_column(
        ForeignKey("grammar_units.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # prompt, prompt_cs, direction, options, tokens: what the learner may see.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Accepted answers, first = shown. Never sent to the client before the exercise is closed.
    answers: Mapped[list] = mapped_column(JSONB, nullable=False)
    explain: Mapped[str] = mapped_column(Text, nullable=False)
    content_flags: Mapped[list[str]] = mapped_column(
        ARRAY(String(16)), default=list, server_default=text("'{}'::varchar[]"), nullable=False
    )
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    unit = relationship("GrammarUnit", back_populates="exercises")


class UserGrammarProgress(TimestampMixin, Base):
    """Per profile and unit. NULL counters mean nothing measured yet; studied_at = lesson done."""

    __tablename__ = "user_grammar_progress"
    __table_args__ = (
        Index("ix_user_grammar_progress_user_next_review", "user_id", "next_review_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    unit_id: Mapped[str] = mapped_column(
        ForeignKey("grammar_units.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[ProgressState] = mapped_column(
        ProgressStateType,
        default=ProgressState.NEW,
        server_default=ProgressState.NEW.value,
        nullable=False,
    )
    studied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 'lesson' or 'placement' (a CEFR placement queued the unit for a check, no lesson needed).
    studied_by: Mapped[str | None] = mapped_column(String(16))
    correct_count: Mapped[int] = mapped_column(default=0, server_default=text("0"), nullable=False)
    error_count: Mapped[int] = mapped_column(default=0, server_default=text("0"), nullable=False)
    review_streak: Mapped[int] = mapped_column(default=0, server_default=text("0"), nullable=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_free_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_decay_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Rule applied correctly in checks often enough (see GRAMMAR_POLICY); starts mastery delay.
    known_since_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy_version: Mapped[str | None] = mapped_column(String(16))


class GrammarSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "grammar_sessions"
    __table_args__ = (
        Index(
            "uq_grammar_sessions_one_active",
            "user_id",
            "language",
            "mode",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        CheckConstraint("mode IN ('learn', 'check')", name="mode"),
        CheckConstraint("status IN ('active', 'completed')", name="status"),
        CheckConstraint("(mode = 'learn') = (unit_id IS NOT NULL)", name="learn_has_unit"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    mode: Mapped[str] = mapped_column(String(8), nullable=False)
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("grammar_units.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(
        String(16), default="active", server_default="active", nullable=False
    )
    policy_version: Mapped[str] = mapped_column(String(16), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )

    unit = relationship("GrammarUnit")
    items = relationship(
        "GrammarSessionItem",
        back_populates="session",
        order_by="GrammarSessionItem.position",
        cascade="all, delete-orphan",
    )


class GrammarSessionItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "grammar_session_items"
    __table_args__ = (
        UniqueConstraint("session_id", "position", name="uq_grammar_session_items_position"),
        CheckConstraint("status IN ('pending', 'done', 'revealed')", name="status"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grammar_sessions.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("grammar_exercises.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    # Remediation: an exercise this profile missed before, brought back on purpose.
    is_remediation: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), default="pending", server_default="pending", nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    first_try_correct: Mapped[bool | None] = mapped_column(Boolean)

    session = relationship("GrammarSession", back_populates="items")
    exercise = relationship("GrammarExercise")


class GrammarAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One graded grammar answer: the mistake log grammar progress is computed from."""

    __tablename__ = "grammar_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_grammar_attempts_idempotency"),
        Index("ix_grammar_attempts_user_unit", "user_id", "unit_id"),
        Index("ix_grammar_attempts_user_time", "user_id", "occurred_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("grammar_exercises.id", ondelete="CASCADE"), nullable=False
    )
    unit_id: Mapped[str] = mapped_column(
        ForeignKey("grammar_units.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("grammar_sessions.id", ondelete="SET NULL")
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("grammar_session_items.id", ondelete="SET NULL")
    )
    mode: Mapped[str] = mapped_column(String(8), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    answer: Mapped[str] = mapped_column(String(500), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    error_tag: Mapped[str | None] = mapped_column(String(32))
    revealed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    counts_as_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
