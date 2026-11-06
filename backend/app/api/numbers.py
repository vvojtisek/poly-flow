"""Number trainer: numbers written out by rules, checked, and spoken. Practice only."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import Auth
from app.api.learning import AUDIO_RESPONSES, TtsDep, _chosen_voice, _speech
from app.domain import numbers as nb
from app.domain.enums import Language

router = APIRouter(prefix="/api/v1/numbers", tags=["practice"])

N = Annotated[int, Query(ge=0, le=nb.MAX)]


class SpellOut(BaseModel):
    n: int
    words: str


class CheckIn(BaseModel):
    language: Language
    n: int = Field(ge=0, le=nb.MAX)
    answer: str = Field(max_length=200)
    # write: digits shown, the learner writes words; read: words or audio, the learner types digits
    direction: Literal["write", "read"] = "write"


class CheckOut(BaseModel):
    correct: bool
    n: int
    words: str


@router.get("/spell", response_model=SpellOut)
async def spell(auth: Auth, n: N, language: Annotated[Language | None, Query()] = None) -> SpellOut:
    lang = language or auth.acting.active_language
    return SpellOut(n=n, words=nb.spell(n, lang))


@router.post("/check", response_model=CheckOut)
async def check(body: CheckIn, auth: Auth) -> CheckOut:
    if body.direction == "read":
        correct = nb.parse_digits(body.answer) == body.n
    else:
        correct = nb.check(body.n, body.answer, body.language)
    return CheckOut(correct=correct, n=body.n, words=nb.spell(body.n, body.language))


@router.get("/audio", response_class=FileResponse, responses=AUDIO_RESPONSES)
async def audio(
    auth: Auth, tts: TtsDep, n: N, language: Annotated[Language | None, Query()] = None
) -> FileResponse:
    lang = language or auth.acting.active_language
    return await _speech(tts, lang, nb.spell(n, lang), _chosen_voice(auth.acting, lang))
