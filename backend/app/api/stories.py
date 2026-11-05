"""Generated reading texts: today's story or dialogue, comprehension questions, audio."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import DB, Auth
from app.api.learning import AUDIO_RESPONSES, TtsDep, _chosen_voice, _speech, get_now
from app.domain.enums import Language
from app.models import DailyStory
from app.services import stories as svc
from app.services.learning import LearningError
from app.services.llm import Llm, get_llm
from app.services.tutor import model_allowed

router = APIRouter(prefix="/api/v1/stories", tags=["stories"])
LlmDep = Annotated[Llm, Depends(get_llm)]
Now = Annotated[datetime, Depends(get_now)]


class LineOut(BaseModel):
    speaker: str | None
    text: str
    cs: str


class GlossOut(BaseModel):
    word: str
    cs: str


class QuestionOut(BaseModel):
    question: str
    options: list[str]
    answered: bool | None  # None = not answered yet; otherwise whether the first answer was right


class StoryOut(BaseModel):
    id: uuid.UUID
    language: Language
    kind: Literal["story", "dialogue"]
    title: str
    lines: list[LineOut]
    glossary: list[GlossOut]
    targets: list[str]
    questions: list[QuestionOut]
    model: str | None
    review_status: Literal["unreviewed"]


class TodayOut(BaseModel):
    model_available: bool
    story: StoryOut | None


class GenerateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Language
    kind: Literal["story", "dialogue"] = "story"


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    choice: int = Field(ge=0, le=9)


class AnswerOut(BaseModel):
    correct: bool
    answer_index: int


def _out(s: DailyStory) -> StoryOut:
    meta = s.generation_meta or {}
    answers = meta.get("answers") or {}
    return StoryOut(
        id=s.id,
        language=s.language,
        kind=meta.get("kind", "story"),
        title=s.title or "",
        lines=[LineOut(**ln) for ln in meta.get("lines", [])],
        glossary=[GlossOut(**g) for g in meta.get("glossary", [])],
        targets=meta.get("targets", []),
        questions=[
            QuestionOut(question=q["question"], options=q["options"], answered=answers.get(str(i)))
            for i, q in enumerate(s.comprehension_questions)
        ],
        model=s.llm_model,
        review_status="unreviewed",
    )


@router.get("/today", response_model=TodayOut)
async def today(language: Language, auth: Auth, db: DB, llm: LlmDep, now: Now) -> TodayOut:
    story = await svc.today(db, auth.acting, language, now)
    shown = story if story is not None and story.status == "generated" else None
    return TodayOut(
        model_available=model_allowed(auth.acting, llm), story=_out(shown) if shown else None
    )


@router.post(
    "/generate",
    response_model=StoryOut,
    responses={
        409: {"description": "model_unavailable / not_enough_words / story_generating"},
        502: {"description": "story_failed: the model's texts did not pass validation"},
    },
)
async def generate(body: GenerateIn, auth: Auth, db: DB, llm: LlmDep, now: Now) -> StoryOut:
    try:
        story = await svc.generate(db, auth.acting, llm, body.language, body.kind, now)
    except LearningError as exc:
        if exc.code == "story_failed":
            await db.commit()  # keep the failure record (not shown to the learner)
        else:
            await db.rollback()
        raise HTTPException(exc.status, exc.code) from exc
    await db.commit()
    return _out(story)


@router.get("/{story_id}", response_model=StoryOut)
async def get_story(story_id: uuid.UUID, auth: Auth, db: DB) -> StoryOut:
    try:
        return _out(await svc.get_story(db, auth.acting, story_id))
    except LearningError as exc:
        raise HTTPException(exc.status, exc.code) from exc


@router.post("/{story_id}/questions/{index}/answer", response_model=AnswerOut)
async def answer(story_id: uuid.UUID, index: int, body: AnswerIn, auth: Auth, db: DB) -> AnswerOut:
    try:
        story = await svc.get_story(db, auth.acting, story_id, for_update=True)
        correct, right = svc.answer_question(story, index, body.choice)
    except LearningError as exc:
        await db.rollback()
        raise HTTPException(exc.status, exc.code) from exc
    await db.commit()
    return AnswerOut(correct=correct, answer_index=right)


@router.get("/{story_id}/audio", response_class=FileResponse, responses=AUDIO_RESPONSES)
async def line_audio(
    story_id: uuid.UUID,
    auth: Auth,
    db: DB,
    tts: TtsDep,
    line: Annotated[int, Query(ge=0)],
) -> FileResponse:
    try:
        story = await svc.get_story(db, auth.acting, story_id)
        text = svc.line_text(story, line)
    except LearningError as exc:
        raise HTTPException(exc.status, exc.code) from exc
    return await _speech(tts, story.language, text, _chosen_voice(auth.acting, story.language))
