"""Telling the time: a clock face and four spoken forms, or a spoken form and four clocks.

Practice only; nothing is recorded. The answer index travels with the question (as in role-play),
because nothing here is knowledge evidence.
"""

import random
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.deps import Auth
from app.api.learning import AUDIO_RESPONSES, TtsDep, _chosen_voice, _speech
from app.domain import clock as ck
from app.domain.enums import Language

router = APIRouter(prefix="/api/v1/clock", tags=["practice"])

Level = Literal["quarters", "five"]
Hour = Annotated[int, Query(ge=1, le=12)]
Minute = Annotated[int, Query(ge=0, le=55, multiple_of=5)]


class TimeOut(BaseModel):
    hour: int
    minute: int
    phrase: str
    czech: str
    digits: str


class QuizOut(BaseModel):
    time: TimeOut
    options: list[TimeOut]  # four, the right one among them
    answer: int


def _out(t: ck.Time, language: Language) -> TimeOut:
    return TimeOut(
        hour=t.hour, minute=t.minute, phrase=ck.say(t, language), czech=ck.czech(t), digits=t.digits
    )


@router.get("/quiz", response_model=QuizOut)
async def quiz(
    auth: Auth,
    language: Annotated[Language | None, Query()] = None,
    level: Level = "quarters",
) -> QuizOut:
    lang = language or auth.acting.active_language
    minutes = (0, 15, 30, 45) if level == "quarters" else ck.MINUTES
    t = ck.Time(random.randint(1, 12), random.choice(minutes))
    wrong = ck.distractors(t)[:3]
    options = [t, *wrong]
    random.shuffle(options)
    return QuizOut(
        time=_out(t, lang), options=[_out(o, lang) for o in options], answer=options.index(t)
    )


@router.get("/audio", response_class=FileResponse, responses=AUDIO_RESPONSES)
async def audio(
    auth: Auth,
    tts: TtsDep,
    hour: Hour,
    minute: Minute,
    language: Annotated[Language | None, Query()] = None,
) -> FileResponse:
    lang = language or auth.acting.active_language
    text = ck.say(ck.Time(hour, minute), lang)
    return await _speech(tts, lang, text, _chosen_voice(auth.acting, lang))
