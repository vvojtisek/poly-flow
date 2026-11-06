"""My dictionary: the profile's own words with state, history and audio."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import DB, Auth
from app.api.learning import AUDIO_RESPONSES, Now, TtsDep, _chosen_voice, _speech
from app.domain.enums import Language
from app.services import notes
from app.services import words as svc
from app.services.learning import LearningError

router = APIRouter(prefix="/api/v1/words", tags=["learning"])
Status = Literal["mastered", "known", "passive", "learning", "seen"]


class WordRowOut(BaseModel):
    id: uuid.UUID
    lemma: str
    gender: str | None
    pos: str
    rank: int
    translation: str
    status: Status
    due: bool
    next_review_at: datetime | None
    correct: int
    errors: int


class WordListOut(BaseModel):
    total: int
    counts: dict[str, int]
    items: list[WordRowOut]


class HistoryOut(BaseModel):
    at: datetime
    correct: bool
    graded: bool
    task: str
    mode: str
    error_tag: str | None


class WordDetailOut(BaseModel):
    id: uuid.UUID
    language: Language
    lemma: str
    gender: str | None
    pos: str
    rank: int
    translation: str
    ipa: str | None
    example: str | None
    review_status: str | None
    status: Status
    passive_known: bool
    active_known: bool
    correct: int
    errors: int
    introduced_at: datetime | None
    introduced_by: str | None
    last_reviewed_at: datetime | None
    next_review_at: datetime | None
    review_streak: int
    history: list[HistoryOut]
    note: str | None = None  # the learner's own memory hook


class NoteIn(BaseModel):
    text: str = Field(max_length=1000)  # trimmed to 280 after collapsing whitespace


class NoteOut(BaseModel):
    note: str | None


def _http(exc: LearningError) -> HTTPException:
    return HTTPException(exc.status, exc.code)


@router.get("", response_model=WordListOut)
async def list_words(
    auth: Auth,
    db: DB,
    now: Now,
    language: Annotated[Language | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=64)] = None,
    status: Status | None = None,
    due: bool = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 60,
) -> WordListOut:
    out = await svc.list_words(
        db,
        auth.acting,
        language or auth.acting.active_language,
        now,
        q=q,
        status=status,
        due=due,
        offset=offset,
        limit=limit,
    )
    return WordListOut(**out)


@router.get("/{item_id}", response_model=WordDetailOut)
async def word(item_id: uuid.UUID, auth: Auth, db: DB, now: Now) -> WordDetailOut:
    try:
        out = WordDetailOut(**await svc.word_detail(db, auth.acting, item_id, now))
    except LearningError as exc:
        raise _http(exc) from exc
    out.note = (await notes.notes_for(db, auth.acting.id, [item_id])).get(item_id)
    return out


@router.put("/{item_id}/note", response_model=NoteOut)
async def put_note(item_id: uuid.UUID, body: NoteIn, auth: Auth, db: DB) -> NoteOut:
    """Set or (with empty text) remove the learner's memory hook for a word."""
    try:
        note = await notes.set_note(db, auth.acting, item_id, body.text)
    except LearningError as exc:
        raise _http(exc) from exc
    await db.commit()
    return NoteOut(note=note)


@router.get("/{item_id}/audio", response_class=FileResponse, responses=AUDIO_RESPONSES)
async def word_audio(
    item_id: uuid.UUID,
    auth: Auth,
    db: DB,
    tts: TtsDep,
    part: Annotated[Literal["word", "example"], Query()] = "word",
) -> FileResponse:
    try:
        language, text = await svc.audio_text(db, auth.acting, item_id, part)
    except LearningError as exc:
        raise _http(exc) from exc
    return await _speech(tts, language, text, _chosen_voice(auth.acting, language))
