"""Review screen data for a finished lesson or check."""

import uuid
from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import DB, Auth
from app.services.learning import LearningError
from app.services.review import session_review

router = APIRouter(prefix="/api/v1/learning/sessions", tags=["learning"])


class ReviewItemOut(BaseModel):
    item_id: uuid.UUID
    lemma: str
    gender: str | None
    translation: str
    task: str
    first_try: bool | None
    answered: str | None
    expected: str
    error: str | None
    passive_known: bool
    active_known: bool
    next_review_at: datetime | None
    note: str | None


class ReviewOut(BaseModel):
    mode: str
    items: list[ReviewItemOut]


@router.get("/{session_id}/review", response_model=ReviewOut)
async def review(session_id: uuid.UUID, auth: Auth, db: DB) -> ReviewOut:
    try:
        mode, items = await session_review(db, auth.acting, session_id)
    except LearningError as exc:
        raise HTTPException(exc.status, exc.code) from exc
    return ReviewOut(mode=mode, items=[ReviewItemOut(**asdict(i)) for i in items])
