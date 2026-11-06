"""Learning insights (statistics) for the acting profile."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import DB, Auth
from app.api.learning import Now
from app.domain.enums import Language
from app.services.insights import day_activity, insights

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


class ForecastWordOut(BaseModel):
    id: uuid.UUID
    lemma: str
    gender: str | None
    translation: str


class ForecastGrammarOut(BaseModel):
    id: str
    title: str
    level: str


class ForecastOut(BaseModel):
    date: date
    words: int
    grammar: int
    word_items: list[ForecastWordOut]
    grammar_items: list[ForecastGrammarOut]


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


class ActivityWordOut(BaseModel):
    id: uuid.UUID
    lemma: str
    gender: str | None
    translation: str
    graded: int
    practice: int


class ActivityGrammarOut(BaseModel):
    id: str
    title: str
    level: str
    graded: int
    practice: int


class ActivityDayOut(BaseModel):
    date: date
    words: list[ActivityWordOut]
    grammar: list[ActivityGrammarOut]


@router.get("", response_model=InsightsOut)
async def get_insights(
    auth: Auth, db: DB, now: Now, language: Annotated[Language | None, Query()] = None
) -> InsightsOut:
    return InsightsOut(
        **await insights(db, auth.acting, language or auth.acting.active_language, now)
    )


@router.get("/day", response_model=ActivityDayOut)
async def get_activity_day(
    auth: Auth,
    db: DB,
    now: Now,
    activity_date: Annotated[date, Query(alias="date")],
    language: Annotated[Language | None, Query()] = None,
) -> ActivityDayOut:
    result = await day_activity(
        db, auth.acting, language or auth.acting.active_language, activity_date, now
    )
    if result is None:
        raise HTTPException(404, "activity_day_not_found")
    return ActivityDayOut(**result)
