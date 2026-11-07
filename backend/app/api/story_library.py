"""Browse the checked-in graded reading library without exposing answer keys."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import DB, Auth
from app.domain.enums import CefrLevel, Language
from app.domain.story_library import LibraryStory, StoryFile
from app.services.safety import blacklist_hits

router = APIRouter(prefix="/api/v1/story-library", tags=["story library"])
_DATA = Path(__file__).resolve().parents[2] / "data" / "stories"


@lru_cache(maxsize=4)
def _library(language: Language) -> StoryFile:
    path = _DATA / f"{language.value}.stories.json"
    return StoryFile.model_validate(json.loads(path.read_text(encoding="utf-8")))


class StorySummary(BaseModel):
    slug: str
    level: CefrLevel
    title: str
    title_cs: str
    line_count: int
    question_count: int
    review_status: str


class LibraryLine(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    speaker: str | None = None
    text: str
    cs: str


class LibraryQuestion(BaseModel):
    question: str
    options: list[str]


class StoryDetail(BaseModel):
    slug: str
    level: CefrLevel
    title: str
    title_cs: str
    lines: list[LibraryLine]
    stretch: list[dict[str, str]]
    questions: list[LibraryQuestion]
    review_status: str


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: int = Field(ge=0, le=3)
    choice: int = Field(ge=0, le=3)


class AnswerOut(BaseModel):
    correct: bool
    answer: int


def _language(auth: Auth, language: Language | None) -> Language:
    selected = language or auth.acting.active_language
    if selected != auth.acting.active_language:
        raise HTTPException(403, "language_not_active")
    return selected


def _story(language: Language, slug: str) -> tuple[StoryFile, LibraryStory]:
    library = _library(language)
    story = next((item for item in library.stories if item.slug == slug), None)
    if story is None:
        raise HTTPException(404, "story_not_found")
    return library, story


async def _child_safe(db: DB, auth: Auth, language: Language, story: LibraryStory) -> bool:
    if not auth.acting.is_child:
        return True
    text = "\n".join(
        [story.title, story.title_cs]
        + [value for line in story.lines for value in (line.text, line.cs)]
        + [question.question for question in story.questions]
        + [option for question in story.questions for option in question.options]
        + [value for word in story.stretch for value in (word.word, word.cs)]
    )
    return not await blacklist_hits(db, text, [language])


@router.get("", response_model=list[StorySummary])
async def list_library(
    auth: Auth,
    db: DB,
    language: Annotated[Language | None, Query()] = None,
    level: Annotated[CefrLevel | None, Query()] = None,
) -> list[StorySummary]:
    selected = _language(auth, language)
    library = _library(selected)
    result = []
    for story in library.stories:
        if level is not None and story.level != level:
            continue
        if not await _child_safe(db, auth, selected, story):
            continue
        result.append(
            StorySummary(
                slug=story.slug,
                level=story.level,
                title=story.title,
                title_cs=story.title_cs,
                line_count=len(story.lines),
                question_count=len(story.questions),
                review_status=library.review_status,
            )
        )
    return result


@router.get("/{slug}", response_model=StoryDetail)
async def get_library_story(
    slug: str,
    auth: Auth,
    db: DB,
    language: Annotated[Language | None, Query()] = None,
) -> StoryDetail:
    selected = _language(auth, language)
    library, story = _story(selected, slug)
    if not await _child_safe(db, auth, selected, story):
        raise HTTPException(404, "story_not_found")
    return StoryDetail(
        slug=story.slug,
        level=story.level,
        title=story.title,
        title_cs=story.title_cs,
        lines=story.lines,
        stretch=[word.model_dump() for word in story.stretch],
        questions=[
            LibraryQuestion(question=q.question, options=q.options) for q in story.questions
        ],
        review_status=library.review_status,
    )


@router.post("/{slug}/answer", response_model=AnswerOut)
async def answer_library_question(
    slug: str,
    body: AnswerIn,
    auth: Auth,
    db: DB,
    language: Annotated[Language | None, Query()] = None,
) -> AnswerOut:
    selected = _language(auth, language)
    _, story = _story(selected, slug)
    if not await _child_safe(db, auth, selected, story):
        raise HTTPException(404, "story_not_found")
    if body.question >= len(story.questions):
        raise HTTPException(422, "question_out_of_range")
    answer = story.questions[body.question].answer_index
    if body.choice >= len(story.questions[body.question].options):
        raise HTTPException(422, "choice_out_of_range")
    return AnswerOut(correct=body.choice == answer, answer=answer)
