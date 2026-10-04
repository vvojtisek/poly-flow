"""Session lifecycle. Callers own the DB transaction (commit/rollback)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import new_token, token_digest
from app.domain.enums import UserRole
from app.models import AuthSession, User

# Refresh last_seen/expiry at most this often to avoid a write per request.
_TOUCH_INTERVAL = timedelta(minutes=5)


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class AuthContext:
    session: AuthSession
    principal: User
    acting: User

    @property
    def can_manage(self) -> bool:
        return self.principal.role == UserRole.ADMIN and self.acting.id == self.principal.id


async def create_session(db: AsyncSession, user: User) -> tuple[AuthSession, str]:
    token = new_token()
    now = utcnow()
    s = AuthSession(
        token_digest=token_digest(token),
        csrf_token=new_token(),
        user_id=user.id,
        acting_user_id=user.id,
        expires_at=now + timedelta(days=get_settings().session_ttl_days),
        last_seen_at=now,
    )
    db.add(s)
    user.last_login_at = now
    await db.flush()
    return s, token


async def resolve_session(db: AsyncSession, token: str) -> AuthContext | None:
    row = (
        await db.execute(select(AuthSession).where(AuthSession.token_digest == token_digest(token)))
    ).scalar_one_or_none()
    now = utcnow()
    if row is None:
        return None
    if row.expires_at <= now:
        await db.delete(row)
        await db.commit()
        return None
    principal = await db.get(User, row.user_id)
    acting = (
        principal if row.acting_user_id == row.user_id else await db.get(User, row.acting_user_id)
    )
    if principal is None or acting is None or not principal.is_active or not acting.is_active:
        return None
    if now - row.last_seen_at > _TOUCH_INTERVAL:
        row.last_seen_at = now
        row.expires_at = now + timedelta(days=get_settings().session_ttl_days)
        await db.commit()
    return AuthContext(session=row, principal=principal, acting=acting)


async def revoke_user_sessions(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Revoke sessions where the user is the principal or the acting profile."""
    await db.execute(
        delete(AuthSession).where(
            (AuthSession.user_id == user_id) | (AuthSession.acting_user_id == user_id)
        )
    )
