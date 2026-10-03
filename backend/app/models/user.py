from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import LanguageType, UserRoleType
from app.domain.enums import Language, UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    # Adults sign in with a password. Children use an optional PIN, or are opened from a
    # parent's session on a shared device; a child without a PIN cannot sign in alone.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    pin_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(
        String(64), default="Europe/Prague", server_default="Europe/Prague", nullable=False
    )
    role: Mapped[UserRole] = mapped_column(
        UserRoleType,
        default=UserRole.LEARNER,
        server_default=UserRole.LEARNER.value,
        nullable=False,
    )
    # Drives the content blacklist in the story pipeline.
    is_child: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    ui_locale: Mapped[str] = mapped_column(
        String(8), default="cs-CZ", server_default="cs-CZ", nullable=False
    )
    active_language: Mapped[Language] = mapped_column(
        LanguageType, default=Language.DE, server_default=Language.DE.value, nullable=False
    )
    # Free-form per-user preferences (daily goal, audio speed, ...); validated at the API layer.
    settings: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )

    # Gamification. Coins are earned only via learning milestones; no energy/hearts.
    xp: Mapped[int] = mapped_column(default=0, server_default=text("0"), nullable=False)
    coins: Mapped[int] = mapped_column(default=0, server_default=text("0"), nullable=False)
    streak_current: Mapped[int] = mapped_column(default=0, server_default=text("0"), nullable=False)
    streak_longest: Mapped[int] = mapped_column(default=0, server_default=text("0"), nullable=False)
    streak_last_active_on: Mapped[date | None] = mapped_column(Date)

    progress = relationship("UserWordProgress", back_populates="user", cascade="all, delete-orphan")
    stories = relationship("DailyStory", back_populates="user", cascade="all, delete-orphan")
