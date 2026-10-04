import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import LanguageType
from app.domain.enums import Language


class SessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class SessionMode(StrEnum):
    LEARN = "learn"  # Lekce: context first, then practice; nothing is graded toward knowledge
    CHECK = "check"  # Ověření: one first-try attempt, no hints; the only source of evidence


class TaskType(StrEnum):
    RECOGNITION = "recognition"  # target word -> pick the Czech meaning
    RECALL = "recall"  # Czech meaning -> write the target word


class TaskStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"  # answered correctly (possibly after retries/hints)
    REVEALED = "revealed"  # learner asked for the answer


def _enum(cls: type[StrEnum], name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


SessionStatusType = _enum(SessionStatus, "learning_session_status")
SessionModeType = _enum(SessionMode, "learning_session_mode")
TaskTypeType = _enum(TaskType, "learning_task_type")
TaskStatusType = _enum(TaskStatus, "learning_task_status")


class LearningSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A lesson or a check: the server issues the tasks; the client cannot add or grade them."""

    __tablename__ = "learning_sessions"
    __table_args__ = (
        # At most one open lesson and one open check per profile and language (resume
        # instead of duplicating).
        Index(
            "uq_learning_sessions_one_active",
            "user_id",
            "language",
            "mode",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    mode: Mapped[SessionMode] = mapped_column(
        SessionModeType,
        default=SessionMode.LEARN,
        server_default=SessionMode.LEARN.value,
        nullable=False,
    )
    # Learn mode: the scene that introduces the lesson's words (None = example sentences only).
    scene_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scenes.id", ondelete="SET NULL"))
    status: Mapped[SessionStatus] = mapped_column(
        SessionStatusType,
        default=SessionStatus.ACTIVE,
        server_default=SessionStatus.ACTIVE.value,
        nullable=False,
    )
    policy_version: Mapped[str] = mapped_column(String(16), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )

    scene = relationship("Scene")
    tasks = relationship(
        "LearningTask",
        back_populates="session",
        order_by="LearningTask.position",
        cascade="all, delete-orphan",
    )


class LearningTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_tasks"
    __table_args__ = (
        UniqueConstraint("session_id", "position", name="uq_learning_tasks_session_position"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    lexicon_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lexicon_items.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    task_type: Mapped[TaskType] = mapped_column(TaskTypeType, nullable=False)
    is_new_item: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Recognition: {"options": ["...", ...], "correct": idx}. Never sent to the client whole.
    payload: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        TaskStatusType,
        default=TaskStatus.PENDING,
        server_default=TaskStatus.PENDING.value,
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    hint_level: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    first_try_correct: Mapped[bool | None] = mapped_column(Boolean)

    session = relationship("LearningSession", back_populates="tasks")
    item = relationship("LexiconItem")


class LearningEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One evaluated attempt. The source of truth that progress is aggregated from."""

    __tablename__ = "learning_events"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_learning_events_idempotency"),
        Index("ix_learning_events_user_item", "user_id", "lexicon_item_id"),
        CheckConstraint("answer_mode IN ('typed', 'spoken')", name="answer_mode"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    lexicon_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lexicon_items.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("learning_sessions.id", ondelete="SET NULL")
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("learning_tasks.id", ondelete="SET NULL")
    )
    task_type: Mapped[TaskType] = mapped_column(TaskTypeType, nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    hint_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
    revealed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    # True only for a first-try, hint-free correct answer: what knowledge thresholds count.
    counts_as_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False)
    orthography_score: Mapped[float | None] = mapped_column(Float)
    # "typed" (written or chosen) or "spoken". For spoken attempts `answer` holds the transcript,
    # `is_correct` whether it says the word, and `transcript_confidence` how sure Whisper was of
    # its transcript. None of these is a pronunciation measurement (phonetic_score stays NULL).
    answer_mode: Mapped[str] = mapped_column(
        String(8), default="typed", server_default="typed", nullable=False
    )
    transcript_confidence: Mapped[float | None] = mapped_column(Float)
    policy_version: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)  # in the profile's timezone
    # Response returned for this attempt, replayed verbatim on duplicate submission.
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)


class GrammarUnlock(TimestampMixin, Base):
    """Persisted unlock: once earned, decay never re-locks grammar."""

    __tablename__ = "grammar_unlocks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, primary_key=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
