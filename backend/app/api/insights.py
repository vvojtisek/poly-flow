"""Learning insights (statistics) for the acting profile."""

import uuid
from datetime import date
from typing import Annotated, Literal

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


class TallyOut(BaseModel):
    answered: int
    correct: int


class WeekOut(BaseModel):
    week: date
    answered: int  # all graded answers of the week
    correct: int
    recognition: TallyOut  # word -> meaning (and other non-production word checks)
    recall: TallyOut  # meaning -> written or spoken word
    grammar: TallyOut


class MistakeItemOut(BaseModel):
    kind: Literal["word", "grammar"]
    id: uuid.UUID
    label: str  # the word with its article, or the topic title
    detail: str  # the Czech meaning, or the topic level
    count: int


class MistakeOut(BaseModel):
    tag: str
    count: int
    items: list[MistakeItemOut] = []  # up to six words/topics behind the tag, most frequent first


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
    fading: int = 0  # recognised once, but no error-free check for longer than the decay window


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
