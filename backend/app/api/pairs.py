"""Minimal pairs listening: the sets for a language and the spoken words. Practice only."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.deps import Auth
from app.api.learning import AUDIO_RESPONSES, TtsDep, _chosen_voice, _speech
from app.domain import minimal_pairs as mp
from app.domain.enums import Language

router = APIRouter(prefix="/api/v1/pairs", tags=["practice"])


class WordOut(BaseModel):
    text: str
    cs: str


class SetOut(BaseModel):
    id: str
    title: str
    hint: str
    pairs: list[tuple[WordOut, WordOut]]


@router.get("", response_model=list[SetOut])
async def list_sets(
    auth: Auth, language: Annotated[Language | None, Query()] = None
) -> list[SetOut]:
    lang = language or auth.acting.active_language
    return [
        SetOut(
            id=s.id,
            title=s.title,
            hint=s.hint,
            pairs=[
                (WordOut(text=a.text, cs=a.cs), WordOut(text=b.text, cs=b.cs)) for a, b in s.pairs
            ],
        )
        for s in mp.sets(lang)
    ]


@router.get("/audio", response_class=FileResponse, responses=AUDIO_RESPONSES)
async def audio(
    auth: Auth,
    tts: TtsDep,
    set: Annotated[str, Query(max_length=32)],
    pair: Annotated[int, Query(ge=0, le=50)],
    side: Annotated[int, Query(ge=0, le=1)],
    language: Annotated[Language | None, Query()] = None,
) -> FileResponse:
    """One word of a pair, spoken. Only words from the fixed sets can be spoken here."""
    lang = language or auth.acting.active_language
    found = mp.find(lang, set)
    if found is None or pair >= len(found.pairs):
        raise HTTPException(404, "pair_not_found")
    word = found.pairs[pair][side]
    return await _speech(tts, lang, word.text, _chosen_voice(auth.acting, lang))
