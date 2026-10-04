from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import LanguageType, UserRoleType
from app.domain.enums import Language, UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        # One sign-in secret per profile: a password or a PIN, never both.
        CheckConstraint("password_hash IS NULL OR pin_hash IS NULL", name="single_credential"),
    )

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    # Every profile signs in on its own with a password or a PIN (admins: password only).
    # Profiles created before 0006 may have neither; an admin can then set one.
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
    # Age-appropriate content filter (lexicon content_flags, story blacklist). Not an access
    # restriction: a child profile can do everything any other learner can.
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
