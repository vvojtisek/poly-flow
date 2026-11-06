"""CEFR placement diagnostic (rozřazovací test, part 2) over HTTP."""

import random
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import DB, Auth
from app.api.learning import AUDIO_RESPONSES, Now, _chosen_voice, _speech
from app.domain.diagnostic import BANDS, DIAGNOSTIC, band_label
from app.domain.enums import Language
from app.domain.voices import DEFAULT_VOICES
from app.services import diagnostic as svc
from app.services.learning import LearningError
from app.services.tts import Tts, get_tts

router = APIRouter(prefix="/api/v1/diagnostic", tags=["learning"])
TtsDep = Annotated[Tts, Depends(get_tts)]


def _http(exc: LearningError) -> HTTPException:
    return HTTPException(exc.status, exc.code)


class LatestOut(BaseModel):
    level: str  # "pre-A1", "A1".."B2", "B2+"
    decided_at: str
    session_id: uuid.UUID | None


class InfoOut(BaseModel):
    available: bool
    review_status: str | None
    items: int
    bands: list[str]
    min_items: int
    max_items: int
    active_session_id: uuid.UUID | None
    latest: LatestOut | None


class StartIn(BaseModel):
    language: Language | None = None


class QuestionOut(BaseModel):
    position: int
    skill: Literal["grammar", "vocabulary", "reading", "listening", "idiom"]
    band: str
    prompt: str
    context: str | None
    has_audio: bool
    options: list[str]
    asked: int
    max_items: int
    theta: float


class StateOut(BaseModel):
    session_id: uuid.UUID
    language: Language
    status: str
    with_listening: bool
    question: QuestionOut | None
    result: dict | None


class AnswerIn(BaseModel):
    position: int = Field(ge=0, le=100)
    choice: str | None = Field(default=None, max_length=300)  # None = "Nevím"


class AnswerOut(BaseModel):
    position: int
    correct: bool
    dont_know: bool
    answer: str
    explain: str
    transcript: str | None
    asked: int
    max_items: int
    theta: float


@router.get("", response_model=InfoOut)
async def info(auth: Auth, db: DB, language: Language | None = None) -> InfoOut:
    lang = language or auth.acting.active_language
    b = svc.bank(lang)
    active = await svc.get_active(db, auth.acting, lang)
    last = await svc.latest(db, auth.acting, lang)
    return InfoOut(
        available=b is not None,
        review_status=b.review_status if b else None,
        items=len(b.items) if b else 0,
        bands=[band_label(x) for x in BANDS],
        min_items=DIAGNOSTIC.min_items,
        max_items=DIAGNOSTIC.max_items,
        active_session_id=active.id if active else None,
        latest=LatestOut(
            level=band_label(last.level),
            decided_at=last.decided_at.isoformat(),
            session_id=last.session_id,
        )
        if last
        else None,
    )


async def _state(db, user, s, rng: random.Random | None = None) -> StateOut:
    question = None
    if s.status == svc.ACTIVE:
        nxt = await svc.advance(db, user, s, rng or random.Random())
        if nxt is not None:
            question = QuestionOut(**svc.question_out(s, *nxt))
    return StateOut(
        session_id=s.id,
        language=s.language,
        status=s.status,
        with_listening=s.with_listening,
        question=question,
        result=s.result if s.status != svc.ACTIVE else None,
    )


@router.post("/sessions", response_model=StateOut)
async def start(body: StartIn, auth: Auth, db: DB, now: Now, tts: TtsDep) -> StateOut:
    """Start (or resume) the diagnostic; listening items need the language's voice installed."""
    lang = body.language or auth.acting.active_language
    with_listening = DEFAULT_VOICES[lang] in await tts.installed()
    try:
        s = await svc.start(db, auth.acting, lang, with_listening=with_listening, now=now)
        out = await _state(db, auth.acting, s)
    except LearningError as exc:
        raise _http(exc) from exc
    await db.commit()
    return out


@router.get("/sessions/{session_id}", response_model=StateOut)
async def state(session_id: uuid.UUID, auth: Auth, db: DB, now: Now) -> StateOut:
    """The pending question, or the result once the test has enough answers."""
    try:
        s = await svc.get_session(db, auth.acting, session_id, lock=True)
        out = await _state(db, auth.acting, s)
        if s.status == svc.ACTIVE and out.question is None:
            await svc.finish(db, auth.acting, s, now)
            out = await _state(db, auth.acting, s)
    except LearningError as exc:
        raise _http(exc) from exc
    await db.commit()
    return out


@router.post("/sessions/{session_id}/answer", response_model=AnswerOut)
async def answer(session_id: uuid.UUID, body: AnswerIn, auth: Auth, db: DB, now: Now) -> AnswerOut:
    """One attempt per question; resending the same position replays the verdict."""
    try:
        out = await svc.answer(db, auth.acting, session_id, body.position, body.choice, now)
    except LearningError as exc:
        raise _http(exc) from exc
    await db.commit()
    return AnswerOut(**out)


@router.post("/sessions/{session_id}/stop", response_model=StateOut)
async def stop(session_id: uuid.UUID, auth: Auth, db: DB, now: Now) -> StateOut:
    """End early: places the learner when enough was answered, else closes without a result."""
    try:
        await svc.abandon(db, auth.acting, session_id, now)
        s = await svc.get_session(db, auth.acting, session_id)
        out = await _state(db, auth.acting, s)
    except LearningError as exc:
        raise _http(exc) from exc
    await db.commit()
    return out


@router.get("/sessions/{session_id}/audio", response_class=FileResponse, responses=AUDIO_RESPONSES)
async def audio(
    session_id: uuid.UUID,
    auth: Auth,
    db: DB,
    tts: TtsDep,
    position: Annotated[int, Query(ge=0, le=100)],
) -> FileResponse:
    """A listening question's recording."""
    try:
        s = await svc.get_session(db, auth.acting, session_id)
        text = svc.audio_text(s, position)
    except LearningError as exc:
        raise _http(exc) from exc
    return await _speech(tts, s.language, text, _chosen_voice(auth.acting, s.language))
