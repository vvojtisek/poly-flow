import logging

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import func, select, text

from app.api.deps import DB, Auth, Limiter
from app.core.config import get_settings
from app.core.security import hash_secret, verify_secret
from app.domain.enums import UserRole
from app.models import User
from app.schemas.profiles import LoginIn, Me, ProfileOut, ReturnIn, SetupIn, SetupStatus, SwitchIn
from app.services.auth import AuthContext, create_session

log = logging.getLogger("polyflow.auth")
router = APIRouter(prefix="/api/v1", tags=["auth"])

# Serialises first-run setup so two concurrent requests cannot both create an admin.
_SETUP_LOCK_KEY = 0x504F4C59  # "POLY"


def _set_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        s.session_cookie_name,
        token,
        max_age=s.session_ttl_days * 86400,
        httponly=True,
        secure=s.cookie_secure,
        samesite="lax",
        path="/",
    )


def _me(ctx: AuthContext) -> Me:
    return Me(
        principal=ProfileOut.from_user(ctx.principal),
        acting=ProfileOut.from_user(ctx.acting),
        csrf_token=ctx.session.csrf_token,
        can_manage=ctx.can_manage,
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/setup", response_model=SetupStatus)
async def setup_status(db: DB) -> SetupStatus:
    count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    return SetupStatus(needs_setup=count == 0)


@router.post("/setup", response_model=Me, status_code=status.HTTP_201_CREATED)
async def setup(body: SetupIn, db: DB, response: Response) -> Me:
    """First run only: create the admin account. There is no open registration."""
    await db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _SETUP_LOCK_KEY})
    if (await db.execute(select(func.count()).select_from(User))).scalar_one() > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "already_set_up")
    admin = User(
        username=body.username,
        display_name=body.display_name,
        password_hash=hash_secret(body.password),
        role=UserRole.ADMIN,
        is_child=False,
        timezone=body.timezone or get_settings().default_timezone,
        settings={},
    )
    db.add(admin)
    await db.flush()
    session, token = await create_session(db, admin)
    await db.commit()
    _set_cookie(response, token)
    log.info("setup_completed", extra={"user_id": str(admin.id)})
    return _me(AuthContext(session=session, principal=admin, acting=admin))


@router.post("/auth/login", response_model=Me)
async def login(
    body: LoginIn, request: Request, db: DB, limiter: Limiter, response: Response
) -> Me:
    s = get_settings()
    user_key, ip_key = f"login:user:{body.username}", f"login:ip:{_client_ip(request)}"
    if await limiter.is_blocked(user_key, s.login_max_attempts) or await limiter.is_blocked(
        ip_key, s.login_max_attempts_per_ip
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_attempts")

    user = (
        await db.execute(select(User).where(User.username == body.username))
    ).scalar_one_or_none()
    # Each profile holds exactly one secret (password or PIN), whatever its content filter.
    stored = None if user is None else (user.password_hash or user.pin_hash)
    ok = verify_secret(stored, body.secret) and user is not None and user.is_active
    if not ok:
        await limiter.record_failure(user_key, s.login_window_s)
        await limiter.record_failure(ip_key, s.login_window_s)
        log.info("login_failed", extra={"username": body.username})
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials")

    await limiter.reset(user_key)
    session, token = await create_session(db, user)
    await db.commit()
    _set_cookie(response, token)
    log.info("login_succeeded", extra={"user_id": str(user.id)})
    return _me(AuthContext(session=session, principal=user, acting=user))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(auth: Auth, db: DB, response: Response) -> None:
    await db.delete(auth.session)
    await db.commit()
    response.delete_cookie(get_settings().session_cookie_name, path="/")


@router.get("/auth/me", response_model=Me)
async def me(auth: Auth) -> Me:
    return _me(auth)


@router.post("/auth/switch", response_model=Me)
async def switch_to_child(body: SwitchIn, auth: Auth, db: DB) -> Me:
    """Open a child profile on this device (shared tablet). Only an admin acting as themselves."""
    if not auth.can_manage:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
    target = await db.get(User, body.profile_id)
    if target is None or not target.is_child or not target.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "profile_not_found")
    auth.session.acting_user_id = target.id
    await db.commit()
    log.info(
        "profile_switched", extra={"user_id": str(auth.principal.id), "acting": str(target.id)}
    )
    return _me(AuthContext(session=auth.session, principal=auth.principal, acting=target))


@router.post("/auth/return", response_model=Me)
async def return_to_parent(
    body: ReturnIn, request: Request, auth: Auth, db: DB, limiter: Limiter
) -> Me:
    """Leave the child profile; requires the admin's password (the child holds the device)."""
    if auth.acting.id == auth.principal.id:
        return _me(auth)
    s = get_settings()
    key = f"reauth:{auth.principal.id}"
    if await limiter.is_blocked(key, s.login_max_attempts):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_attempts")
    if not verify_secret(auth.principal.password_hash, body.password):
        await limiter.record_failure(key, s.login_window_s)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials")
    await limiter.reset(key)
    auth.session.acting_user_id = auth.principal.id
    await db.commit()
    return _me(AuthContext(session=auth.session, principal=auth.principal, acting=auth.principal))
