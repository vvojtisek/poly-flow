import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import DB, Auth
from app.domain.enums import Language
from app.models import LearningSession, LearningTask
from app.models.learning import TaskStatus, TaskType
from app.schemas.learning import (
    AnswerIn,
    AnswerOut,
    NextOut,
    Option,
    ProgressOut,
    RevealIn,
    SessionOut,
    StartIn,
    StartOut,
    TaskOut,
)
from app.services import learning as svc

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


def get_now() -> datetime:
    return datetime.now(UTC)


Now = Annotated[datetime, Depends(get_now)]


def _http(exc: svc.LearningError) -> HTTPException:
    return HTTPException(exc.status, exc.code)


def _session_out(s: LearningSession) -> SessionOut:
    return SessionOut(
        id=s.id,
        language=s.language,
        status=s.status,
        total=len(s.tasks),
        remaining=sum(t.status == TaskStatus.PENDING for t in s.tasks),
        created_at=s.created_at,
        completed_at=s.completed_at,
        summary=s.summary,
    )


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
    s = await svc.start_session(db, auth.acting, language, now)
    await db.commit()
    return StartOut(session=_session_out(s) if s else None)


@router.get("/sessions/current", response_model=StartOut)
async def current(
    auth: Auth, db: DB, language: Annotated[Language | None, Query()] = None
) -> StartOut:
    s = await svc.get_active_session(db, auth.acting, language or auth.acting.active_language)
    return StartOut(session=_session_out(s) if s else None)


@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: uuid.UUID, auth: Auth, db: DB) -> SessionOut:
    try:
        return _session_out(await svc.get_session(db, auth.acting, session_id))
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
    return NextOut(task=_task_out(task, len(s.tasks)))


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
    return _session_out(s)


@router.get("/progress", response_model=ProgressOut)
async def progress(
    auth: Auth, db: DB, now: Now, language: Annotated[Language | None, Query()] = None
) -> ProgressOut:
    return await svc.progress_overview(
        db, auth.acting, language or auth.acting.active_language, now
    )
