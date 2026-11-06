import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, Auth
from app.api.learning import Now
from app.domain.enums import Language
from app.domain.grammar import GRAMMAR_OPEN_FROM_START, LEVELS
from app.models import (
    GrammarSession,
    GrammarSessionItem,
    GrammarUnit,
    GrammarUnlock,
    User,
    UserGrammarProgress,
)
from app.schemas.grammar import (
    ExerciseOut,
    GrammarAnswerIn,
    GrammarAnswerOut,
    GrammarCheckIn,
    GrammarNextOut,
    GrammarRevealIn,
    GrammarSessionOut,
    GrammarStartOut,
    LevelOut,
    TreeOut,
    UnitOut,
    UnitSummaryOut,
)
from app.services import grammar as svc
from app.services.learning import LearningError

router = APIRouter(prefix="/api/v1/grammar", tags=["grammar"])


def _http(exc: LearningError) -> HTTPException:
    return HTTPException(exc.status, exc.code)


async def _is_open(db: AsyncSession, user: User, language: Language) -> bool:
    if GRAMMAR_OPEN_FROM_START:
        return True
    return await db.get(GrammarUnlock, (user.id, language)) is not None


async def _require_open(db: AsyncSession, user: User, language: Language) -> None:
    if not await _is_open(db, user, language):
        raise HTTPException(403, "grammar_locked")


def _unit_out(unit: GrammarUnit, status: str = "new") -> UnitOut:
    return UnitOut(
        id=unit.id,
        level=unit.level,
        title=unit.title,
        summary=unit.summary,
        objective=unit.objective,
        notes=unit.notes,
        examples=unit.examples,
        status=status,
        review_status=unit.review_status,
        source=unit.source,
    )


async def _unit_status(db: AsyncSession, user: User, unit: GrammarUnit) -> str:
    p = await db.get(UserGrammarProgress, (user.id, unit.id))
    return svc.UnitStatus(unit, p, 0, 0).status


async def _session_out(db: AsyncSession, user: User, s: GrammarSession) -> GrammarSessionOut:
    unit = None
    if s.unit is not None:
        unit = _unit_out(s.unit, await _unit_status(db, user, s.unit))
    return GrammarSessionOut(
        id=s.id,
        language=s.language,
        mode=s.mode,
        status=s.status,
        unit=unit,
        total=len(s.items),
        remaining=sum(i.status == "pending" for i in s.items),
        summary=s.summary,
    )


def _exercise_out(item: GrammarSessionItem, total: int) -> ExerciseOut:
    ex = item.exercise
    p = ex.payload
    return ExerciseOut(
        item_id=item.id,
        session_id=item.session_id,
        position=item.position,
        total=total,
        kind=ex.kind,
        prompt=p["prompt"],
        prompt_cs=p.get("prompt_cs"),
        direction=p.get("direction"),
        options=p.get("options"),
        tokens=p.get("tokens"),
        unit_id=ex.unit_id,
        unit_title=ex.unit.title,
        is_remediation=item.is_remediation,
        status=item.status,
        attempts=item.attempts,
    )


@router.get("", response_model=TreeOut)
async def get_tree(
    auth: Auth, db: DB, now: Now, language: Annotated[Language | None, Query()] = None
) -> TreeOut:
    user = auth.acting
    lang = language or user.active_language
    units = await svc.tree(db, user, lang, now)
    by_level: dict = {}
    statuses = set()
    for u in units:
        p = u.progress
        statuses.add(u.unit.review_status)
        by_level.setdefault(u.unit.level, []).append(
            UnitSummaryOut(
                id=u.unit.id,
                level=u.unit.level,
                title=u.unit.title,
                summary=u.unit.summary,
                objective=u.unit.objective,
                status=u.status,
                exercises=u.exercises,
                due=bool(p and p.studied_at and p.next_review_at and p.next_review_at <= now),
                recent_errors=u.recent_errors,
                next_review_at=p.next_review_at if p and p.studied_at else None,
            )
        )
    lesson = await svc.get_active(db, user, lang, svc.LEARN)
    check = await svc.get_active(db, user, lang, svc.CHECK)
    return TreeOut(
        language=lang,
        open=await _is_open(db, user, lang),
        due=await svc.due_count(db, user, lang, now),
        recommended=svc.recommended(units),
        review_status=(None if not statuses else statuses.pop() if len(statuses) == 1 else "mixed"),
        levels=[LevelOut(level=lv, units=by_level[lv]) for lv in LEVELS if lv in by_level],
        active_lesson_unit=lesson.unit_id if lesson else None,
        active_check_session_id=check.id if check else None,
    )


@router.get("/units/{unit_id}", response_model=UnitOut)
async def get_unit(unit_id: str, auth: Auth, db: DB) -> UnitOut:
    try:
        unit = await svc.get_unit(db, auth.acting, unit_id)
    except LearningError as exc:
        raise _http(exc) from exc
    return _unit_out(unit, await _unit_status(db, auth.acting, unit))


@router.post("/units/{unit_id}/lesson", response_model=GrammarStartOut)
async def start_lesson(unit_id: str, auth: Auth, db: DB, now: Now) -> GrammarStartOut:
    try:
        unit = await svc.get_unit(db, auth.acting, unit_id)
        await _require_open(db, auth.acting, unit.language)
        s = await svc.start_learn(db, auth.acting, unit_id, now)
    except LearningError as exc:
        await db.rollback()
        raise _http(exc) from exc
    await db.commit()
    s = await svc.get_session(db, auth.acting, s.id)
    return GrammarStartOut(session=await _session_out(db, auth.acting, s))


@router.post("/check", response_model=GrammarStartOut)
async def start_check(body: GrammarCheckIn, auth: Auth, db: DB, now: Now) -> GrammarStartOut:
    lang = body.language or auth.acting.active_language
    await _require_open(db, auth.acting, lang)
    s = await svc.start_check(db, auth.acting, lang, now)
    await db.commit()
    if s is None:
        return GrammarStartOut(session=None)
    s = await svc.get_session(db, auth.acting, s.id)
    return GrammarStartOut(session=await _session_out(db, auth.acting, s))


@router.get("/sessions/{session_id}", response_model=GrammarSessionOut)
async def get_session(session_id: uuid.UUID, auth: Auth, db: DB) -> GrammarSessionOut:
    try:
        s = await svc.get_session(db, auth.acting, session_id)
    except LearningError as exc:
        raise _http(exc) from exc
    return await _session_out(db, auth.acting, s)


@router.get("/sessions/{session_id}/next", response_model=GrammarNextOut)
async def next_item(session_id: uuid.UUID, auth: Auth, db: DB) -> GrammarNextOut:
    try:
        s = await svc.get_session(db, auth.acting, session_id)
    except LearningError as exc:
        raise _http(exc) from exc
    item = svc.next_pending(s)
    return GrammarNextOut(item=_exercise_out(item, len(s.items)) if item else None)


@router.post("/sessions/{session_id}/complete", response_model=GrammarSessionOut)
async def complete(session_id: uuid.UUID, auth: Auth, db: DB, now: Now) -> GrammarSessionOut:
    try:
        s = await svc.complete(db, auth.acting, session_id, now)
    except LearningError as exc:
        raise _http(exc) from exc
    await db.commit()
    s = await svc.get_session(db, auth.acting, s.id)
    return await _session_out(db, auth.acting, s)


@router.post("/items/{item_id}/answer", response_model=GrammarAnswerOut)
async def answer(
    item_id: uuid.UUID, body: GrammarAnswerIn, auth: Auth, db: DB, now: Now
) -> GrammarAnswerOut:
    try:
        r = await svc.submit(
            db,
            auth.acting,
            item_id,
            idempotency_key=body.idempotency_key,
            now=now,
            choice=body.choice,
            text=body.text,
        )
    except LearningError as exc:
        await db.rollback()
        raise _http(exc) from exc
    await db.commit()
    return GrammarAnswerOut(**r)


@router.post("/items/{item_id}/reveal", response_model=GrammarAnswerOut)
async def reveal(
    item_id: uuid.UUID, body: GrammarRevealIn, auth: Auth, db: DB, now: Now
) -> GrammarAnswerOut:
    try:
        r = await svc.submit(
            db, auth.acting, item_id, idempotency_key=body.idempotency_key, now=now, reveal=True
        )
    except LearningError as exc:
        await db.rollback()
        raise _http(exc) from exc
    await db.commit()
    return GrammarAnswerOut(**r)
