"""Role-play: replay a lesson scene as one of its speakers. Ungraded practice, nothing recorded.

Offered: scenes the profile finished a lesson on, or whose words it has all met (placement).
Hidden: scenes with a word this profile may not see, the same rule as lessons.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import aliased

from app.api.deps import DB, Auth
from app.api.learning import AUDIO_RESPONSES, TtsDep, _chosen_voice, _speech
from app.domain import roleplay as rp
from app.domain.dictation import compare, score
from app.domain.enums import Language
from app.models import LearningSession, LexiconItem, Scene, SceneWord, User, UserWordProgress
from app.models.learning import SessionStatus
from app.services.learning import _suitable

router = APIRouter(prefix="/api/v1/roleplay", tags=["learning"])


class SceneSummaryOut(BaseModel):
    id: uuid.UUID
    title: str
    speakers: list[str]
    lines: int


class ScriptLineOut(BaseModel):
    speaker: str
    text: str
    cs: str
    mine: bool
    options: list[str] | None = None  # on the learner's lines
    answer: int | None = None


class ScriptOut(BaseModel):
    id: uuid.UUID
    title: str
    role: str
    speakers: list[str]
    lines: list[ScriptLineOut]


class CheckIn(BaseModel):
    line: int = Field(ge=0, le=200)
    text: str = Field(max_length=600)


class MarkOut(BaseModel):
    expected: str | None
    typed: str | None
    verdict: str


class CheckOut(BaseModel):
    marks: list[MarkOut]
    score: float


def _visible(user: User):
    hidden = aliased(LexiconItem)
    return ~(
        select(SceneWord.scene_id)
        .join(hidden, hidden.id == SceneWord.lexicon_item_id)
        .where(SceneWord.scene_id == Scene.id, ~_suitable(user, hidden))
        .exists()
    )


def _met(user: User):
    """The profile finished a lesson on the scene, or met all its words another way (placement)."""
    p = UserWordProgress
    lesson = (
        select(LearningSession.id)
        .where(
            LearningSession.user_id == user.id,
            LearningSession.scene_id == Scene.id,
            LearningSession.status == SessionStatus.COMPLETED,
        )
        .exists()
    )
    unmet_word = (
        select(SceneWord.scene_id)
        .outerjoin(p, (p.lexicon_item_id == SceneWord.lexicon_item_id) & (p.user_id == user.id))
        .where(SceneWord.scene_id == Scene.id, p.introduced_at.is_(None))
        .exists()
    )
    return or_(lesson, ~unmet_word)


async def _scenes(db, user: User, language: Language) -> list[Scene]:
    return list(
        (
            await db.execute(
                select(Scene)
                .where(Scene.language == language, _visible(user), _met(user))
                .order_by(Scene.position)
            )
        ).scalars()
    )


async def _scene(db, user: User, scene_id: uuid.UUID) -> tuple[Scene, list[rp.Line]]:
    scene = (
        await db.execute(select(Scene).where(Scene.id == scene_id, _visible(user), _met(user)))
    ).scalar_one_or_none()
    if scene is None:
        raise HTTPException(404, "scene_not_found")
    lines = [rp.plain(x) for x in scene.lines]
    if not rp.playable(lines):
        raise HTTPException(404, "scene_not_playable")
    return scene, lines


@router.get("", response_model=list[SceneSummaryOut])
async def list_scenes(
    auth: Auth, db: DB, language: Annotated[Language | None, Query()] = None
) -> list[SceneSummaryOut]:
    out = []
    for scene in await _scenes(db, auth.acting, language or auth.acting.active_language):
        lines = [rp.plain(x) for x in scene.lines]
        if rp.playable(lines):
            out.append(
                SceneSummaryOut(
                    id=scene.id, title=scene.title_cs, speakers=rp.speakers(lines), lines=len(lines)
                )
            )
    return out


@router.get("/{scene_id}", response_model=ScriptOut)
async def script(
    scene_id: uuid.UUID, auth: Auth, db: DB, role: Annotated[str, Query(max_length=64)]
) -> ScriptOut:
    scene, lines = await _scene(db, auth.acting, scene_id)
    if role not in rp.speakers(lines):
        raise HTTPException(422, "unknown_role")
    # Distractors from the other scenes this profile may see (met or not: they are only shown).
    others = (
        await db.execute(
            select(Scene.lines).where(
                Scene.language == scene.language, Scene.id != scene.id, _visible(auth.acting)
            )
        )
    ).scalars()
    other_lines = [rp.plain(x).text for ls in others for x in ls]
    out = []
    for i, ln in enumerate(lines):
        mine = ln.speaker == role
        opts, answer = (
            rp.options(lines, i, other_lines, f"{scene.id}:{role}") if mine else (None, None)
        )
        out.append(
            ScriptLineOut(
                speaker=ln.speaker or "",
                text=ln.text,
                cs=ln.cs,
                mine=mine,
                options=opts,
                answer=answer,
            )
        )
    return ScriptOut(
        id=scene.id, title=scene.title_cs, role=role, speakers=rp.speakers(lines), lines=out
    )


@router.post("/{scene_id}/check", response_model=CheckOut)
async def check(scene_id: uuid.UUID, body: CheckIn, auth: Auth, db: DB) -> CheckOut:
    _, lines = await _scene(db, auth.acting, scene_id)
    if body.line >= len(lines):
        raise HTTPException(422, "unknown_line")
    marks = compare(lines[body.line].text, body.text)
    return CheckOut(
        marks=[MarkOut(expected=m.expected, typed=m.typed, verdict=m.verdict) for m in marks],
        score=round(score(marks), 3),
    )


@router.get("/{scene_id}/audio", response_class=FileResponse, responses=AUDIO_RESPONSES)
async def line_audio(
    scene_id: uuid.UUID,
    auth: Auth,
    db: DB,
    tts: TtsDep,
    line: Annotated[int, Query(ge=0, le=200)],
) -> FileResponse:
    scene, lines = await _scene(db, auth.acting, scene_id)
    if line >= len(lines):
        raise HTTPException(404, "unknown_line")
    return await _speech(
        tts, scene.language, lines[line].text, _chosen_voice(auth.acting, scene.language)
    )
