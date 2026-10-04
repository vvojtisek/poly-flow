import uuid
from typing import Annotated, Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.domain.enums import Language, UserRole

Username = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, pattern=r"^[a-z0-9_.-]{3,32}$"),
]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Password = Annotated[str, StringConstraints(min_length=8, max_length=256)]
Pin = Annotated[str, StringConstraints(pattern=r"^[0-9]{4,8}$")]


def _check_tz(v: str | None) -> str | None:
    if v is not None and v not in available_timezones():
        raise ValueError("unknown IANA timezone")
    return v


class ProfileSettings(BaseModel):
    """Per-profile preferences stored in users.settings."""

    model_config = ConfigDict(extra="forbid")

    daily_goal_minutes: int = Field(default=10, ge=5, le=120)
    audio_rate: float = Field(default=1.0, ge=0.5, le=1.5)
    autoplay_audio: bool = True


class ProfileOut(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str
    role: UserRole
    is_child: bool
    is_active: bool
    has_pin: bool
    has_password: bool
    active_language: Language
    timezone: str
    settings: ProfileSettings

    @classmethod
    def from_user(cls, user) -> "ProfileOut":
        return cls(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            is_child=user.is_child,
            is_active=user.is_active,
            has_pin=user.pin_hash is not None,
            has_password=user.password_hash is not None,
            active_language=user.active_language,
            timezone=user.timezone,
            settings=ProfileSettings.model_validate(user.settings or {}),
        )


class SetupStatus(BaseModel):
    needs_setup: bool


class SetupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Username
    display_name: DisplayName
    password: Password
    timezone: str | None = None

    _tz = field_validator("timezone")(_check_tz)


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=64)]
    secret: Annotated[str, StringConstraints(min_length=1, max_length=256)]  # password or PIN


class Me(BaseModel):
    principal: ProfileOut
    acting: ProfileOut
    csrf_token: str
    can_manage: bool  # admin acting as themselves (not handed over to a child profile)


class SwitchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: uuid.UUID


class ReturnIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: Annotated[str, StringConstraints(min_length=1, max_length=256)]


class ProfileCreate(BaseModel):
    """Every profile gets its own sign-in: a password or a PIN. The learner picks their
    languages themselves, so there is no language field here."""

    model_config = ConfigDict(extra="forbid")

    username: Username
    display_name: DisplayName
    kind: Literal["adult", "child"]  # child = age-appropriate content filter
    password: Password | None = None
    pin: Pin | None = None
    timezone: str | None = None

    _tz = field_validator("timezone")(_check_tz)


class ProfileAdminUpdate(BaseModel):
    """Admin-managed fields: access (credentials, active) and the content filter.

    Learning choices (language, goals, audio, timezone) belong to the profile itself and are
    deliberately absent; role is not updatable.
    """

    model_config = ConfigDict(extra="forbid")

    display_name: DisplayName | None = None
    password: Password | None = None  # replaces a PIN
    pin: Pin | None = None  # replaces a password; not for admins
    is_active: bool | None = None
    is_child: bool | None = None


class ProfileSelfUpdate(BaseModel):
    """What a profile may change about itself. extra=forbid rejects role/is_child/etc."""

    model_config = ConfigDict(extra="forbid")

    display_name: DisplayName | None = None
    active_language: Language | None = None
    timezone: str | None = None
    settings: ProfileSettings | None = None

    _tz = field_validator("timezone")(_check_tz)
