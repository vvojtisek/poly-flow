import math
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, Auth
from app.core.config import get_settings
from app.domain.enums import Language
from app.domain.level_exam import EXAM
from app.domain.placement import PLACEMENT
from app.models import LearningSession, LearningTask, LexiconItem
from app.models.learning import SessionMode, TaskStatus, TaskType
from app.schemas.learning import (
    AnswerIn,
    AnswerOut,
    IdempotencyKey,
    LevelsInfo,
    LevelStatusOut,
    NextOut,
    Option,
    PlacementInfo,
    PlacementOut,
    PlacementSkipIn,
    ProgressOut,
    RevealIn,
    SceneLineOut,
    SceneOut,
    SegmentOut,
    SessionOut,
    StartIn,
    StartOut,
    TaskOut,
    WordCard,
)
from app.services import learning as svc
from app.services import level_exam as exam_svc
from app.services import placement as placement_svc
from app.services.stt import Stt, SttBusy, SttRejected, SttUnavailable, get_stt
from app.services.tts import Tts, TtsUnavailable, get_tts

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


def get_now() -> datetime:
    return datetime.now(UTC)


Now = Annotated[datetime, Depends(get_now)]
TtsDep = Annotated[Tts, Depends(get_tts)]
SttDep = Annotated[Stt, Depends(get_stt)]


def _http(exc: svc.LearningError) -> HTTPException:
    return HTTPException(exc.status, exc.code)


async def _session_out(db: AsyncSession, s: LearningSession) -> SessionOut:
    out = SessionOut(
        id=s.id,
        language=s.language,
        mode=s.mode,
        status=s.status,
        total=len(s.tasks),
        remaining=sum(t.status == TaskStatus.PENDING for t in s.tasks),
        created_at=s.created_at,
        completed_at=s.completed_at,
        summary=s.summary,
    )
    if s.mode != SessionMode.LEARN:
        return out
    new_items = list({t.item.id: t.item for t in s.tasks if t.is_new_item}.values())
    new_ids = {i.id for i in new_items}
    lines = s.scene.lines if s.scene else []
    ids = {uuid.UUID(seg["item"]) for line in lines for seg in line["segments"] if seg.get("item")}
    gloss = (
        dict(
            (
                await db.execute(
                    select(LexiconItem.id, LexiconItem.translation_cs).where(
                        LexiconItem.id.in_(ids)
                    )
                )
            ).all()
        )
        if ids
        else {}
    )
    scene_lines: list[SceneLineOut] = []
    context: dict[uuid.UUID, tuple[str, str]] = {}
    for line in lines:
        segs = []
        for seg in line["segments"]:
            item_id = uuid.UUID(seg["item"]) if seg.get("item") else None
            if item_id not in gloss:
                item_id = None  # the word left the lexicon: plain text
            segs.append(
                SegmentOut(
                    text=seg["t"],
                    item_id=item_id,
                    gloss=gloss.get(item_id) if item_id else None,
                    new=item_id in new_ids,
                )
            )
            if item_id in new_ids:
                context.setdefault(item_id, ("".join(x["t"] for x in line["segments"]), line["cs"]))
        scene_lines.append(SceneLineOut(speaker=line.get("speaker"), cs=line["cs"], segments=segs))
    if s.scene:
        out.scene = SceneOut(title=s.scene.title_cs, lines=scene_lines)
    out.words = [
        WordCard(
            id=i.id,
            lemma=i.lemma,
            pos=i.pos,
            gender=i.gender,
            ipa=i.ipa,
            translation=i.translation_cs,
            context=context[i.id][0] if i.id in context else i.example_sentence,
            context_cs=context[i.id][1] if i.id in context else None,
        )
        for i in new_items
    ]
    return out


def _task_out(task: LearningTask, total: int) -> TaskOut:
    item = task.item
    recognition = task.task_type == TaskType.RECOGNITION
    options = svc.visible_options(task)
    return TaskOut(
        id=task.id,
        session_id=task.session_id,
        position=task.position,
        total=total,
        type=task.task_type,
        status=task.status,
        attempts=task.attempts,
        hint_level=task.hint_level,
        is_new_item=task.is_new_item,
        prompt=item.lemma if recognition else item.translation_cs,
        pos=item.pos,
        gender=item.gender,
        example=item.example_sentence if recognition else None,
        options=[Option(id=i, text=t) for i, t in options] if options is not None else None,
        hint=svc.hint_text(task),
        cloze=svc.cloze(task),
    )


@router.post("/sessions", response_model=StartOut)
async def start(body: StartIn, auth: Auth, db: DB, now: Now) -> StartOut:
    language = body.language or auth.acting.active_language
    try:
        s = await svc.start_session(
            db, auth.acting, language, now, mode=body.mode, level=body.level
        )
    except svc.LearningError as exc:
        await db.rollback()
        raise _http(exc) from exc
    await db.commit()
    return StartOut(session=await _session_out(db, s) if s else None)


@router.get("/sessions/current", response_model=StartOut)
async def current(
    auth: Auth,
    db: DB,
    language: Annotated[Language | None, Query()] = None,
    mode: Annotated[SessionMode, Query()] = SessionMode.LEARN,
) -> StartOut:
    s = await svc.get_active_session(db, auth.acting, language or auth.acting.active_language, mode)
    return StartOut(session=await _session_out(db, s) if s else None)


@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: uuid.UUID, auth: Auth, db: DB) -> SessionOut:
    try:
        return await _session_out(db, await svc.get_session(db, auth.acting, session_id))
    except svc.LearningError as exc:
        raise _http(exc) from exc


@router.get("/sessions/{session_id}/next", response_model=NextOut)
async def next_task(session_id: uuid.UUID, auth: Auth, db: DB, now: Now) -> NextOut:
    try:
        s = await svc.get_session(db, auth.acting, session_id)
    except svc.LearningError as exc:
        raise _http(exc) from exc
    task = svc.next_pending(s)
    if task is None:
        return NextOut(task=None)
    await svc.mark_seen(db, auth.acting, task.item, now)
    await db.commit()
    # A placement test's length depends on the answers: show its upper bound.
    total = PLACEMENT.max_items if s.mode == SessionMode.PLACEMENT else len(s.tasks)
    return NextOut(task=_task_out(task, total))


@router.post("/tasks/{task_id}/hint", response_model=TaskOut)
async def hint(task_id: uuid.UUID, auth: Auth, db: DB) -> TaskOut:
    try:
        task = await svc.use_hint(db, auth.acting, task_id)
    except svc.LearningError as exc:
        raise _http(exc) from exc
    await db.commit()
    total = len((await svc.get_session(db, auth.acting, task.session_id)).tasks)
    return _task_out(task, total)


@router.post("/tasks/{task_id}/answer", response_model=AnswerOut)
async def answer(task_id: uuid.UUID, body: AnswerIn, auth: Auth, db: DB, now: Now) -> AnswerOut:
    try:
        result = await svc.submit_answer(
            db,
            auth.acting,
            task_id,
            idempotency_key=body.idempotency_key,
            now=now,
            choice=body.choice,
            text=body.text,
        )
    except svc.LearningError as exc:
        await db.rollback()
        raise _http(exc) from exc
    await db.commit()
    return AnswerOut.model_validate(result)


async def _read_recording(request: Request) -> tuple[bytes, str]:
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if not (content_type.startswith("audio/") or content_type == "video/webm"):
        raise HTTPException(415, "audio_required")
    limit = get_settings().speech_max_upload_bytes
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > limit:
        raise HTTPException(413, "audio_too_large")
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > limit:
            raise HTTPException(413, "audio_too_large")
    if not body:
        raise HTTPException(422, "audio_invalid")
    return bytes(body), request.headers["content-type"]


@router.post(
    "/tasks/{task_id}/speech",
    response_model=AnswerOut,
    openapi_extra={
        "requestBody": {"content": {"audio/*": {"schema": {"type": "string", "format": "binary"}}}}
    },
    responses={
        413: {"description": "audio_too_large / audio_too_long"},
        415: {"description": "audio_required: send the recording with an audio/* type"},
        422: {"description": "audio_invalid: empty or not decodable"},
        429: {"description": "speech_busy: the STT queue is full; retry later"},
        503: {"description": "speech_unavailable: the STT service is not running"},
    },
)
async def answer_by_speech(
    task_id: uuid.UUID,
    request: Request,
    idempotency_key: Annotated[IdempotencyKey, Query()],
    auth: Auth,
    db: DB,
    stt: SttDep,
    now: Now,
) -> AnswerOut:
    """Answer a recall task by voice. The recording is transcribed and discarded, never stored."""
    if (cached := await svc.replay(db, auth.acting, idempotency_key)) is not None:
        return AnswerOut.model_validate(cached)
    try:
        task = await svc.get_task(db, auth.acting, task_id)
    except svc.LearningError as exc:
        raise _http(exc) from exc
    audio, content_type = await _read_recording(request)
    try:
        words = await stt.transcribe(task.item.language, audio, content_type)
    except SttRejected as exc:
        raise HTTPException(413 if exc.code == "audio_too_long" else 422, exc.code) from exc
    except SttBusy as exc:
        raise HTTPException(429, "speech_busy") from exc
    except SttUnavailable as exc:
        raise HTTPException(503, "speech_unavailable") from exc
    try:
        result = await svc.submit_answer(
            db, auth.acting, task_id, idempotency_key=idempotency_key, now=now, spoken=words
        )
    except svc.LearningError as exc:
        await db.rollback()
        raise _http(exc) from exc
    await db.commit()
    return AnswerOut.model_validate(result)


@router.post("/tasks/{task_id}/reveal", response_model=AnswerOut)
async def reveal(task_id: uuid.UUID, body: RevealIn, auth: Auth, db: DB, now: Now) -> AnswerOut:
    try:
        result = await svc.submit_answer(
            db, auth.acting, task_id, idempotency_key=body.idempotency_key, now=now, reveal=True
        )
    except svc.LearningError as exc:
        await db.rollback()
        raise _http(exc) from exc
    await db.commit()
    return AnswerOut.model_validate(result)


@router.post("/sessions/{session_id}/complete", response_model=SessionOut)
async def complete(session_id: uuid.UUID, auth: Auth, db: DB, now: Now) -> SessionOut:
    try:
        s = await svc.complete_session(db, auth.acting, session_id, now)
    except svc.LearningError as exc:
        raise _http(exc) from exc
    await db.commit()
    return await _session_out(db, s)


@router.get("/progress", response_model=ProgressOut)
async def progress(
    auth: Auth, db: DB, now: Now, language: Annotated[Language | None, Query()] = None
) -> ProgressOut:
    return await svc.progress_overview(
        db, auth.acting, language or auth.acting.active_language, now
    )


@router.get("/placement", response_model=PlacementInfo)
async def placement_info(
    auth: Auth, db: DB, language: Annotated[Language | None, Query()] = None
) -> PlacementInfo:
    """What a placement test can cover for this profile now, and the latest decision."""
    language = language or auth.acting.active_language
    placed = await placement_svc.get_placement(db, auth.acting, language)
    active = await svc.get_active_session(db, auth.acting, language, SessionMode.PLACEMENT)
    return PlacementInfo(
        language=language,
        ceiling=await placement_svc.ceiling(db, auth.acting, language),
        max_questions=PLACEMENT.max_items,
        placement=PlacementOut.model_validate(placed, from_attributes=True) if placed else None,
        active_session_id=active.id if active else None,
    )


@router.post("/placement/skip", status_code=204)
async def placement_skip(body: PlacementSkipIn, auth: Auth, db: DB, now: Now) -> None:
    """Start from the beginning: the test is no longer offered (it can still be taken)."""
    await placement_svc.skip(db, auth.acting, body.language or auth.acting.active_language, now)
    await db.commit()


@router.get("/levels", response_model=LevelsInfo)
async def levels(
    auth: Auth, db: DB, now: Now, language: Annotated[Language | None, Query()] = None
) -> LevelsInfo:
    """The vocabulary level exams (A1-B2) for this language: which are earned, open or locked."""
    language = language or auth.acting.active_language
    rows = await exam_svc.statuses(db, auth.acting, language, now)
    return LevelsInfo(
        language=language,
        questions=EXAM.questions,
        pass_correct=EXAM.pass_correct,
        levels=[
            LevelStatusOut(
                level=st.level,
                low=st.low,
                high=st.high,
                state=st.state,
                lexicon_items=st.lexicon_items,
                pool=st.pool,
                known=st.known,
                ready_known=math.ceil(st.pool * EXAM.ready_share),
                earned_at=st.earned_at,
                retry_from=st.retry_from,
                active_session_id=st.active_session_id,
                last_correct=st.last_correct,
                last_asked=st.last_asked,
            )
            for st in rows
        ],
    )


# ---------------------------------------------------------------- audio

AUDIO_RESPONSES: dict[int | str, dict] = {
    200: {"content": {"audio/wav": {}}, "description": "Speech as WAV"},
    404: {"description": "audio_not_found"},
    409: {"description": "audio_would_reveal: the task asks for this word"},
    503: {"description": "audio_unavailable: the TTS service is not running"},
}


def _chosen_voice(user, language: Language) -> str | None:
    """The profile's voice for `language` (validated when saved; unknown ids fall back)."""
    chosen = (user.settings or {}).get("voices") or {}
    return chosen.get(language.value) if isinstance(chosen, dict) else None


async def _speech(tts: Tts, language: Language, text: str, voice: str | None) -> FileResponse:
    try:
        path = await tts.speech(language, text, voice)
    except TtsUnavailable as exc:
        raise HTTPException(503, "audio_unavailable") from exc
    return FileResponse(
        path, media_type="audio/wav", headers={"Cache-Control": "private, max-age=86400"}
    )


@router.get("/sessions/{session_id}/audio", response_class=FileResponse, responses=AUDIO_RESPONSES)
async def session_audio(
    session_id: uuid.UUID,
    auth: Auth,
    db: DB,
    tts: TtsDep,
    line: Annotated[int | None, Query(ge=0)] = None,
    item: Annotated[uuid.UUID | None, Query()] = None,
    part: Annotated[Literal["word", "context"], Query()] = "word",
) -> FileResponse:
    """A lesson's scene line (`line`) or new word (`item`, its `word` or `context`) spoken."""
    if (line is None) == (item is None):
        raise HTTPException(422, "line_or_item_required")
    try:
        s = await svc.get_session(db, auth.acting, session_id)
        text = svc.session_audio_text(s, line, item, part)
    except svc.LearningError as exc:
        raise _http(exc) from exc
    return await _speech(tts, s.language, text, _chosen_voice(auth.acting, s.language))


@router.get("/tasks/{task_id}/audio", response_class=FileResponse, responses=AUDIO_RESPONSES)
async def task_audio(
    task_id: uuid.UUID,
    auth: Auth,
    db: DB,
    tts: TtsDep,
    part: Annotated[Literal["word", "example"], Query()] = "word",
) -> FileResponse:
    """A task's word or example sentence spoken; a pending recall task stays silent."""
    try:
        task = await svc.get_task(db, auth.acting, task_id)
        text = svc.task_audio_text(task, part)
    except svc.LearningError as exc:
        raise _http(exc) from exc
    lang = task.item.language
    return await _speech(tts, lang, text, _chosen_voice(auth.acting, lang))
