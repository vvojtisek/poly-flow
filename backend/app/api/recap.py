"""Weekly recap (Týden v kostce) for the acting profile."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import DB, Auth
from app.api.learning import Now
from app.domain.enums import Language
from app.services.recap import recap

router = APIRouter(prefix="/api/v1/insights/recap", tags=["learning"])


class WeekOut(BaseModel):
    active_days: int
    graded: int
    correct: int
    practice: int
    introduced: int
    newly_known: int
    accuracy: float | None  # None: nothing graded that week (unknown, not 0 %)


class HardWordOut(BaseModel):
    id: uuid.UUID
    lemma: str
    gender: str | None
    translation: str
    misses: int


class RecapOut(BaseModel):
    language: Language
    from_: date = Field(alias="from")
    to: date
    this_week: WeekOut
    last_week: WeekOut
    accuracy_trend: str | None
    hard_words: list[HardWordOut]
    due_now: int
    due_next_7_days: int
    suggestion: str

    model_config = {"populate_by_name": True}


def _week(w) -> WeekOut:
    return WeekOut(
        active_days=w.active_days,
        graded=w.graded,
        correct=w.correct,
        practice=w.practice,
        introduced=w.introduced,
        newly_known=w.newly_known,
        accuracy=w.accuracy,
    )


@router.get("", response_model=RecapOut, response_model_by_alias=True)
async def weekly_recap(
    auth: Auth, db: DB, now: Now, language: Annotated[Language | None, Query()] = None
) -> RecapOut:
    data = await recap(db, auth.acting, language or auth.acting.active_language, now)
    return RecapOut(
        **{
            **data,
            "from": data["from"],
            "this_week": _week(data["this_week"]),
            "last_week": _week(data["last_week"]),
        }
    )
