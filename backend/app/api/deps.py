import hmac
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.services.auth import AuthContext, resolve_session
from app.services.rate_limit import AttemptLimiter, RedisAttemptLimiter

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "X-CSRF-Token"


async def get_db() -> AsyncIterator[AsyncSession]:
    async for s in get_session():
        yield s


DB = Annotated[AsyncSession, Depends(get_db)]


@lru_cache
def _redis() -> Redis:
    return Redis.from_url(get_settings().redis_url)


def get_limiter() -> AttemptLimiter:
    return RedisAttemptLimiter(_redis())


Limiter = Annotated[AttemptLimiter, Depends(get_limiter)]


def _unauthorized() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "not_authenticated")


async def get_auth(request: Request, db: DB) -> AuthContext:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise _unauthorized()
    ctx = await resolve_session(db, token)
    if ctx is None:
        raise _unauthorized()
    if request.method not in SAFE_METHODS:
        sent = request.headers.get(CSRF_HEADER, "")
        if not hmac.compare_digest(sent, ctx.session.csrf_token):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "csrf_failed")
    return ctx


Auth = Annotated[AuthContext, Depends(get_auth)]


async def require_manager(auth: Auth) -> AuthContext:
    """Admin acting as themselves (not handed over to a child profile)."""
    if not auth.can_manage:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
    return auth


Manager = Annotated[AuthContext, Depends(require_manager)]
