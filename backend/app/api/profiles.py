import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, Auth, Manager
from app.core.config import get_settings
from app.core.security import hash_secret
from app.domain.enums import UserRole
from app.models import User
from app.schemas.profiles import (
    ProfileAdminUpdate,
    ProfileCreate,
    ProfileOut,
    ProfileSelfUpdate,
    ProfileSettings,
)
from app.services.auth import revoke_user_sessions

router = APIRouter(prefix="/api/v1", tags=["profiles"])


@router.get("/me/profile", response_model=ProfileOut)
async def get_own_profile(auth: Auth) -> ProfileOut:
    return ProfileOut.from_user(auth.acting)


@router.patch("/me/profile", response_model=ProfileOut)
async def update_own_profile(body: ProfileSelfUpdate, auth: Auth, db: DB) -> ProfileOut:
    user = auth.acting
    for field in ("display_name", "active_language", "timezone"):
        value = getattr(body, field)
        if value is not None:
            setattr(user, field, value)
    if body.settings is not None:
        # Partial: fields the request leaves out keep their stored value.
        changed = body.settings.model_dump(mode="json", exclude_unset=True)
        if user.is_child and changed.get("learn_profanity"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "profanity_adults_only")
        stored = ProfileSettings.from_stored(user.settings).model_dump(mode="json")
        user.settings = {**stored, **changed}
    await db.commit()
    return ProfileOut.from_user(user)


@router.get("/profiles", response_model=list[ProfileOut])
async def list_profiles(_: Manager, db: DB) -> list[ProfileOut]:
    users = (await db.execute(select(User).order_by(User.created_at))).scalars().all()
    return [ProfileOut.from_user(u) for u in users]


@router.post("/profiles", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(body: ProfileCreate, _: Manager, db: DB) -> ProfileOut:
    """Admin grants access. Language and other learning choices stay with the new profile."""
    if (body.password is None) == (body.pin is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "password_or_pin_required")
    user = User(
        username=body.username,
        display_name=body.display_name,
        role=UserRole.LEARNER,
        is_child=body.kind == "child",
        password_hash=hash_secret(body.password) if body.password else None,
        pin_hash=hash_secret(body.pin) if body.pin else None,
        timezone=body.timezone or get_settings().default_timezone,
        settings={},
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "username_taken") from exc
    return ProfileOut.from_user(user)


async def _managed(db: DB, profile_id: uuid.UUID) -> User:
    user = await db.get(User, profile_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "profile_not_found")
    return user


@router.patch("/profiles/{profile_id}", response_model=ProfileOut)
async def update_profile(
    profile_id: uuid.UUID, body: ProfileAdminUpdate, auth: Manager, db: DB
) -> ProfileOut:
    user = await _managed(db, profile_id)
    is_self = user.id == auth.principal.id
    is_admin = user.role == UserRole.ADMIN
    if body.password is not None and body.pin is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "password_or_pin_required")
    if body.pin is not None:
        if is_admin:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "admin_needs_password")
        user.pin_hash, user.password_hash = hash_secret(body.pin), None
    if body.password is not None:
        user.password_hash, user.pin_hash = hash_secret(body.password), None
    if body.is_active is not None:
        if is_self and not body.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "cannot_deactivate_self")
        user.is_active = body.is_active
    if body.is_child is not None:
        if is_admin and body.is_child:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "admin_cannot_be_child")
        user.is_child = body.is_child
    if body.display_name is not None:
        user.display_name = body.display_name
    # Changed credentials or deactivation end that profile's other sessions.
    if (body.password or body.pin or body.is_active is False) and not is_self:
        await revoke_user_sessions(db, user.id)
    await db.commit()
    return ProfileOut.from_user(user)


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(profile_id: uuid.UUID, auth: Manager, db: DB) -> None:
    user = await _managed(db, profile_id)
    if user.id == auth.principal.id or user.role == UserRole.ADMIN:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "cannot_delete_admin")
    await db.delete(user)  # cascades to sessions and learning data
    await db.commit()
