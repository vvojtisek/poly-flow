"""Today's plan: the next steps and the day's (estimated) learning time."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import DB, Auth
from app.api.learning import Now
from app.domain.enums import Language
from app.services.today import plan

router = APIRouter(prefix="/api/v1/today", tags=["learning"])


class StepOut(BaseModel):
    kind: Literal["check", "grammar_check", "lesson", "reading"]
    count: int
    minutes: int


class TodayOut(BaseModel):
    language: Language
    date: date
    minutes_today: int
    answers_today: int
    goal_minutes: int
    steps: list[StepOut]
    tomorrow_due: int


@router.get("", response_model=TodayOut)
async def today(
    auth: Auth, db: DB, now: Now, language: Annotated[Language | None, Query()] = None
) -> TodayOut:
    return TodayOut(**await plan(db, auth.acting, language or auth.acting.active_language, now))
