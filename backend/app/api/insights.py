"""Learning insights (statistics) for the acting profile."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import DB, Auth
from app.api.learning import Now
from app.domain.enums import Language
from app.services.insights import insights

router = APIRouter(prefix="/api/v1/insights", tags=["learning"])


class DayOut(BaseModel):
    date: date
    graded: int
    practice: int


class WeekOut(BaseModel):
    week: date
    answered: int
    correct: int


class MistakeOut(BaseModel):
    tag: str
    count: int


class ForecastOut(BaseModel):
    date: date
    words: int
    grammar: int


class FunnelOut(BaseModel):
    introduced: int
    passive: int
    active: int
    known: int
    mastered: int


class InsightsOut(BaseModel):
    language: Language
    today: date
    heatmap: list[DayOut]
    active_days: int
    accuracy: list[WeekOut]
    mistakes: list[MistakeOut]
    forecast: list[ForecastOut]
    funnel: FunnelOut


@router.get("", response_model=InsightsOut)
async def get_insights(
    auth: Auth, db: DB, now: Now, language: Annotated[Language | None, Query()] = None
) -> InsightsOut:
    return InsightsOut(
        **await insights(db, auth.acting, language or auth.acting.active_language, now)
    )
