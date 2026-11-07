"""Generated reading texts: today's story or dialogue, comprehension questions, audio."""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import DB, Auth
from app.api.learning import AUDIO_RESPONSES, TtsDep, _chosen_voice, _speech, get_now
from app.domain.enums import CefrLevel, Language
from app.models import DailyStory
from app.services import library as library_svc
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
    story_date: date
    kind: Literal["story", "dialogue"]
    title: str
    lines: list[LineOut]
    glossary: list[GlossOut]
    targets: list[str]
    questions: list[QuestionOut]
    model: str | None
    source_collection: str | None
    review_status: Literal["unreviewed"]


class StoryArchiveOut(BaseModel):
    id: uuid.UUID
    story_date: date
    title: str
    kind: Literal["story", "dialogue"]
    source_collection: str | None
    targets: list[str]


class TodayOut(BaseModel):
    model_available: bool
    story: StoryOut | None


class GenerateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Language
    kind: Literal["story", "dialogue"] = "story"
    collection_id: uuid.UUID | None = None


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
        story_date=s.story_date,
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
        source_collection=meta.get("source_collection"),
        review_status="unreviewed",
    )


def _archive_out(s: DailyStory) -> StoryArchiveOut:
    meta = s.generation_meta or {}
    return StoryArchiveOut(
        id=s.id,
        story_date=s.story_date,
        title=s.title or "",
        kind=meta.get("kind", "story"),
        source_collection=meta.get("source_collection"),
        targets=meta.get("targets", []),
    )


@router.get("/today", response_model=TodayOut)
async def today(language: Language, auth: Auth, db: DB, llm: LlmDep, now: Now) -> TodayOut:
    story = await svc.today(db, auth.acting, language, now)
    shown = story if story is not None and story.status == "generated" else None
    return TodayOut(
        model_available=model_allowed(auth.acting, llm), story=_out(shown) if shown else None
    )


@router.get("/archive", response_model=list[StoryArchiveOut])
async def story_archive(
    auth: Auth,
    db: DB,
    language: Annotated[Language | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=60)] = 30,
) -> list[StoryArchiveOut]:
    rows = await svc.archive(db, auth.acting, language or auth.acting.active_language, limit=limit)
    return [_archive_out(story) for story in rows]


class LibraryLineOut(BaseModel):
    speaker: str | None
    text: str
    cs: str


class LibraryStoryOut(BaseModel):
    slug: str
    level: CefrLevel
    title: str
    title_cs: str
    kind: Literal["story", "dialogue"]  # dialogue = every line has a speaker
    lines: int
    stretch: int


class LibraryOut(BaseModel):
    language: Language
    review_status: Literal["unreviewed", "reviewed"]
    source: str
    license: str
    stories: list[LibraryStoryOut]


def _kind(s) -> Literal["story", "dialogue"]:
    return "dialogue" if all(ln.speaker for ln in s.lines) else "story"


@router.get("/library", response_model=LibraryOut)
async def story_library(
    auth: Auth, db: DB, language: Annotated[Language | None, Query()] = None
) -> LibraryOut:
    """The curated graded stories of a language that pass the content gate. Ungraded reading."""
    lang = language or auth.acting.active_language
    lib = await library_svc.library(db, auth.acting, lang)
    if lib is None:
        return LibraryOut(
            language=lang, review_status="unreviewed", source="", license="", stories=[]
        )
    return LibraryOut(
        language=lang,
        review_status=lib.file.review_status,
        source=lib.file.source,
        license=lib.file.license,
        stories=[
            LibraryStoryOut(
                slug=s.slug,
                level=s.level,
                title=s.title,
                title_cs=s.title_cs,
                kind=_kind(s),
                lines=len(s.lines),
                stretch=len(s.stretch),
            )
            for s in lib.stories
        ],
    )


class LibraryQuestionOut(BaseModel):
    question: str
    options: list[str]


class LibraryReadOut(BaseModel):
    slug: str
    questions: list[LibraryQuestionOut]  # answers stay on the server
    stretch: list[GlossOut]  # words from the level above, with a Czech gloss
    language: Language
    level: CefrLevel
    title: str
    title_cs: str
    kind: Literal["story", "dialogue"]
    lines: list[LibraryLineOut]
    review_status: Literal["unreviewed", "reviewed"]


@router.get("/library/{slug}", response_model=LibraryReadOut)
async def library_story(
    slug: Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")],
    auth: Auth,
    db: DB,
    language: Annotated[Language | None, Query()] = None,
) -> LibraryReadOut:
    lang = language or auth.acting.active_language
    try:
        lib = await library_svc.story(db, auth.acting, lang, slug)
    except LearningError as exc:
        raise HTTPException(exc.status, exc.code) from exc
    s = lib.stories[0]
    return LibraryReadOut(
        slug=s.slug,
        language=lang,
        level=s.level,
        title=s.title,
        title_cs=s.title_cs,
        kind=_kind(s),
        lines=[LibraryLineOut(speaker=ln.speaker, text=ln.text, cs=ln.cs) for ln in s.lines],
        stretch=[GlossOut(word=w.word, cs=w.cs) for w in s.stretch],
        questions=[LibraryQuestionOut(question=q.question, options=q.options) for q in s.questions],
        review_status=lib.file.review_status,
    )


@router.post(
    "/generate",
    response_model=StoryOut,
    responses={
        409: {
            "description": (
                "model_unavailable / not_enough_words / story_generating / collection_too_small"
            )
        },
        502: {"description": "story_failed: the model's texts did not pass validation"},
    },
)
async def generate(body: GenerateIn, auth: Auth, db: DB, llm: LlmDep, now: Now) -> StoryOut:
    try:
        story = await svc.generate(
            db,
            auth.acting,
            llm,
            body.language,
            body.kind,
            now,
            collection_id=body.collection_id,
        )
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


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story(story_id: uuid.UUID, auth: Auth, db: DB) -> Response:
    try:
        await svc.delete_archived_story(db, auth.acting, story_id)
    except LearningError as exc:
        await db.rollback()
        raise HTTPException(exc.status, exc.code) from exc
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.get("/library/{slug}/audio", response_class=FileResponse, responses=AUDIO_RESPONSES)
async def library_line_audio(
    slug: Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")],
    auth: Auth,
    db: DB,
    tts: TtsDep,
    line: Annotated[int, Query(ge=0, le=40)],
    language: Annotated[Language | None, Query()] = None,
) -> FileResponse:
    """One line of a library story read aloud, through the same gate as the text itself."""
    lang = language or auth.acting.active_language
    try:
        lib = await library_svc.story(db, auth.acting, lang, slug)
    except LearningError as exc:
        raise HTTPException(exc.status, exc.code) from exc
    lines = lib.stories[0].lines
    if line >= len(lines):
        raise HTTPException(404, "unknown_line")
    return await _speech(tts, lang, lines[line].text, _chosen_voice(auth.acting, lang))


@router.post("/library/{slug}/questions/{index}/answer", response_model=AnswerOut)
async def library_answer(
    slug: Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")],
    index: Annotated[int, Path(ge=0, le=9)],
    body: AnswerIn,
    auth: Auth,
    db: DB,
    language: Annotated[Language | None, Query()] = None,
) -> AnswerOut:
    """A comprehension check while reading: says whether the choice is right. Nothing is stored."""
    lang = language or auth.acting.active_language
    try:
        lib = await library_svc.story(db, auth.acting, lang, slug)
    except LearningError as exc:
        raise HTTPException(exc.status, exc.code) from exc
    questions = lib.stories[0].questions
    if index >= len(questions):
        raise HTTPException(404, "unknown_question")
    q = questions[index]
    if body.choice >= len(q.options):
        raise HTTPException(422, "invalid_choice")
    return AnswerOut(correct=body.choice == q.answer_index, answer_index=q.answer_index)
