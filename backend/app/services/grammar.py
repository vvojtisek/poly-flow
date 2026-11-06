"""Grammar lessons and checks (plan P5). Callers own the transaction; `now` is injected.

- learn: one unit's notes, then all its exercises with retries; a wrong answer shows the right
  one with the rule's explanation. Plus a few exercises the profile missed recently in other
  units (remediation). Never evidence; completing it marks the unit studied, checkable from the
  next local day.
- check: due studied units, a few exercises each (missed ones first). One attempt, no retries.
  The only evidence that moves a unit's review schedule.
"""

import random
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, select, true, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import ContentFlag, Language, ProgressState
from app.domain.grammar import ExerciseKind, GrammarPack, blank, grade
from app.domain.learning_policy import GRAMMAR_POLICY as POLICY
from app.models import (
    GrammarAttempt,
    GrammarExercise,
    GrammarSession,
    GrammarSessionItem,
    GrammarUnit,
    User,
    UserGrammarProgress,
)
from app.services.learning import LearningError, next_local_midnight, wants_profanity

LEARN, CHECK = "learn", "check"


# ---------------------------------------------------------------- content import


async def upsert_pack(db: AsyncSession, pack: GrammarPack) -> tuple[int, int]:
    """Insert or update a pack's units and exercises by id. Progress and attempts are kept.

    Units and exercises that left the pack are deactivated, not deleted: attempts and progress
    referencing them stay readable, and they are no longer offered.
    """
    unit_ids, ex_ids = [], []
    # Positions are unique per language/unit: park the current ones first so a reordered pack
    # does not collide with itself.
    await db.execute(
        update(GrammarUnit)
        .where(GrammarUnit.language == pack.language)
        .values(position=-GrammarUnit.position - 1_000_000)
    )
    for pos, u in enumerate(pack.units):
        unit_ids.append(u.id)
        values = dict(
            id=u.id,
            language=pack.language,
            level=u.level,
            position=pos,
            title=u.title,
            summary=u.summary,
            notes=[n.model_dump(exclude_none=True) for n in u.notes],
            examples=[e.model_dump() for e in u.examples],
            source=pack.source,
            license=pack.license,
            revision=pack.revision,
            review_status=pack.review_status,
            active=True,
        )
        stmt = pg_insert(GrammarUnit).values(**values)
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[GrammarUnit.id],
                set_={k: stmt.excluded[k] for k in values if k != "id"}
                | {"updated_at": func.now()},
            )
        )
        await db.execute(
            update(GrammarExercise)
            .where(GrammarExercise.unit_id == u.id)
            .values(position=-GrammarExercise.position - 1_000_000)
        )
        for epos, e in enumerate(u.exercises):
            ex_ids.append(e.id)
            payload = {
                k: v
                for k, v in {
                    "prompt": e.prompt,
                    "prompt_cs": e.prompt_cs,
                    "direction": e.direction,
                    "options": e.options,
                    "tokens": e.tokens,
                }.items()
                if v is not None
            }
            ev = dict(
                id=e.id,
                unit_id=u.id,
                position=epos,
                kind=e.kind.value,
                payload=payload,
                answers=e.answers,
                explain=e.explain,
                content_flags=[f.value for f in e.content_flags],
                active=True,
            )
            st = pg_insert(GrammarExercise).values(**ev)
            await db.execute(
                st.on_conflict_do_update(
                    index_elements=[GrammarExercise.id],
                    set_={k: st.excluded[k] for k in ev if k != "id"} | {"updated_at": func.now()},
                )
            )
    # Retire what the pack no longer has (moved to unique negative positions above).
    await db.execute(
        update(GrammarUnit)
        .where(GrammarUnit.language == pack.language, GrammarUnit.id.not_in(unit_ids))
        .values(active=False)
    )
    await db.execute(
        update(GrammarExercise)
        .where(
            GrammarExercise.unit_id.in_(
                select(GrammarUnit.id).where(GrammarUnit.language == pack.language)
            ),
            GrammarExercise.id.not_in(ex_ids),
        )
        .values(active=False)
    )
    return len(unit_ids), len(ex_ids)


# ---------------------------------------------------------------- filters


def _suitable(user: User):
    """Child profiles never get a flagged exercise; adults skip profanity unless opted in."""
    if user.is_child:
        return func.cardinality(GrammarExercise.content_flags) == 0
    if wants_profanity(user):
        return true()
    return ~GrammarExercise.content_flags.contains([ContentFlag.PROFANITY.value])


def _live_exercises(user: User):
    return and_(GrammarExercise.active.is_(True), _suitable(user))


# ---------------------------------------------------------------- tree


@dataclass(slots=True)
class UnitStatus:
    unit: GrammarUnit
    progress: UserGrammarProgress | None
    exercises: int
    recent_errors: int

    @property
    def status(self) -> str:
        p = self.progress
        if p is None or p.studied_at is None:
            return "new"
        if p.state == ProgressState.MASTERED:
            return "mastered"
        if p.known_since_at is not None:
            return "known"
        return "studied"


async def tree(db: AsyncSession, user: User, language: Language, now: datetime):
    units = list(
        (
            await db.execute(
                select(GrammarUnit)
                .where(GrammarUnit.language == language, GrammarUnit.active.is_(True))
                .order_by(GrammarUnit.position)
            )
        ).scalars()
    )
    ids = [u.id for u in units]
    if not ids:
        return []
    progress = {
        p.unit_id: p
        for p in (
            await db.execute(
                select(UserGrammarProgress).where(
                    UserGrammarProgress.user_id == user.id, UserGrammarProgress.unit_id.in_(ids)
                )
            )
        ).scalars()
    }
    counts = dict(
        (
            await db.execute(
                select(GrammarExercise.unit_id, func.count())
                .where(GrammarExercise.unit_id.in_(ids), _live_exercises(user))
                .group_by(GrammarExercise.unit_id)
            )
        ).all()
    )
    errors = dict(
        (
            await db.execute(
                select(GrammarAttempt.unit_id, func.count())
                .where(
                    GrammarAttempt.user_id == user.id,
                    GrammarAttempt.unit_id.in_(ids),
                    GrammarAttempt.mode == CHECK,
                    GrammarAttempt.is_correct.is_(False),
                    GrammarAttempt.occurred_at >= now - POLICY.remediation_window,
                )
                .group_by(GrammarAttempt.unit_id)
            )
        ).all()
    )
    return [
        UnitStatus(u, progress.get(u.id), counts.get(u.id, 0), errors.get(u.id, 0))
        for u in units
        if counts.get(u.id, 0) > 0
    ]


async def get_unit(db: AsyncSession, user: User, unit_id: str) -> GrammarUnit:
    unit = (
        await db.execute(
            select(GrammarUnit).where(GrammarUnit.id == unit_id, GrammarUnit.active.is_(True))
        )
    ).scalar_one_or_none()
    if unit is None:
        raise LearningError("unit_not_found", 404)
    return unit


async def due_count(db: AsyncSession, user: User, language: Language, now: datetime) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(UserGrammarProgress)
            .join(GrammarUnit, GrammarUnit.id == UserGrammarProgress.unit_id)
            .where(
                UserGrammarProgress.user_id == user.id,
                GrammarUnit.language == language,
                GrammarUnit.active.is_(True),
                UserGrammarProgress.studied_at.is_not(None),
                UserGrammarProgress.next_review_at <= now,
            )
        )
    ).scalar_one()


# ---------------------------------------------------------------- sessions


def _with_items():
    return (
        selectinload(GrammarSession.items)
        .selectinload(GrammarSessionItem.exercise)
        .selectinload(GrammarExercise.unit),
        selectinload(GrammarSession.unit),
    )


async def get_session(db: AsyncSession, user: User, session_id: uuid.UUID) -> GrammarSession:
    s = (
        await db.execute(
            select(GrammarSession)
            .where(GrammarSession.id == session_id, GrammarSession.user_id == user.id)
            .options(*_with_items())
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if s is None:
        raise LearningError("session_not_found", 404)
    return s


async def get_active(
    db: AsyncSession, user: User, language: Language, mode: str
) -> GrammarSession | None:
    return (
        await db.execute(
            select(GrammarSession)
            .where(
                GrammarSession.user_id == user.id,
                GrammarSession.language == language,
                GrammarSession.mode == mode,
                GrammarSession.status == "active",
            )
            .options(*_with_items())
        )
    ).scalar_one_or_none()


async def recently_missed(
    db: AsyncSession,
    user: User,
    language: Language,
    now: datetime,
    *,
    exclude_unit: str | None = None,
    limit: int,
) -> list[GrammarExercise]:
    """Exercises whose latest check answer was wrong, within the remediation window."""
    latest = (
        select(
            GrammarAttempt.exercise_id,
            GrammarAttempt.is_correct,
            GrammarAttempt.occurred_at,
            func.row_number()
            .over(
                partition_by=GrammarAttempt.exercise_id,
                order_by=GrammarAttempt.occurred_at.desc(),
            )
            .label("rn"),
        )
        .where(
            GrammarAttempt.user_id == user.id,
            GrammarAttempt.mode == CHECK,
            GrammarAttempt.occurred_at >= now - POLICY.remediation_window,
        )
        .subquery()
    )
    q = (
        select(GrammarExercise)
        .join(latest, latest.c.exercise_id == GrammarExercise.id)
        .join(GrammarUnit, GrammarUnit.id == GrammarExercise.unit_id)
        .where(
            latest.c.rn == 1,
            latest.c.is_correct.is_(False),
            GrammarUnit.language == language,
            GrammarUnit.active.is_(True),
            _live_exercises(user),
        )
        .order_by(latest.c.occurred_at.desc())
        .limit(limit)
    )
    if exclude_unit:
        q = q.where(GrammarExercise.unit_id != exclude_unit)
    return list((await db.execute(q)).scalars())


async def _create(
    db: AsyncSession,
    user: User,
    language: Language,
    mode: str,
    unit_id: str | None,
    exercises: list[tuple[GrammarExercise, bool]],
) -> GrammarSession | None:
    session = GrammarSession(
        user_id=user.id,
        language=language,
        mode=mode,
        unit_id=unit_id,
        policy_version=POLICY.version,
        summary={},
    )
    try:
        async with db.begin_nested():
            db.add(session)
            await db.flush()
    except IntegrityError:
        return await get_active(db, user, language, mode)  # a concurrent start won
    for pos, (ex, remediation) in enumerate(exercises):
        db.add(
            GrammarSessionItem(
                session_id=session.id, exercise_id=ex.id, position=pos, is_remediation=remediation
            )
        )
    await db.flush()
    return await get_session(db, user, session.id)


async def start_learn(
    db: AsyncSession, user: User, unit_id: str, now: datetime, rng: random.Random | None = None
) -> GrammarSession:
    """Open (or resume) the lesson of one unit. Another unit's open lesson is set aside."""
    unit = await get_unit(db, user, unit_id)
    existing = await get_active(db, user, unit.language, LEARN)
    if existing is not None:
        if existing.unit_id == unit.id:
            return existing
        existing.status = "completed"
        existing.completed_at = now
        existing.summary = {**_summary(existing), "abandoned": True}
        await db.flush()
    exercises = list(
        (
            await db.execute(
                select(GrammarExercise)
                .where(GrammarExercise.unit_id == unit.id, _live_exercises(user))
                .order_by(GrammarExercise.position)
            )
        ).scalars()
    )
    if not exercises:
        raise LearningError("unit_empty", 404)
    plan = [(e, False) for e in exercises]
    missed = await recently_missed(
        db, user, unit.language, now, exclude_unit=unit.id, limit=POLICY.lesson_remediation
    )
    plan += [(e, True) for e in missed]
    session = await _create(db, user, unit.language, LEARN, unit.id, plan)
    assert session is not None
    return session


async def start_check(
    db: AsyncSession,
    user: User,
    language: Language,
    now: datetime,
    rng: random.Random | None = None,
) -> GrammarSession | None:
    """Resume the open grammar check, or build one from due units. None = nothing due."""
    existing = await get_active(db, user, language, CHECK)
    if existing is not None:
        return existing
    rng = rng or random.Random()
    due = list(
        (
            await db.execute(
                select(UserGrammarProgress)
                .join(GrammarUnit, GrammarUnit.id == UserGrammarProgress.unit_id)
                .where(
                    UserGrammarProgress.user_id == user.id,
                    GrammarUnit.language == language,
                    GrammarUnit.active.is_(True),
                    UserGrammarProgress.studied_at.is_not(None),
                    UserGrammarProgress.next_review_at <= now,
                )
                .order_by(UserGrammarProgress.next_review_at, GrammarUnit.position)
                .limit(POLICY.check_max_units)
            )
        ).scalars()
    )
    if not due:
        return None
    unit_ids = [p.unit_id for p in due]
    exercises = list(
        (
            await db.execute(
                select(GrammarExercise).where(
                    GrammarExercise.unit_id.in_(unit_ids), _live_exercises(user)
                )
            )
        ).scalars()
    )
    # Per exercise: was it missed last time, and how often was it asked in checks.
    stats = {
        ex_id: (n, last_wrong)
        for ex_id, n, last_wrong in (
            await db.execute(
                select(
                    GrammarAttempt.exercise_id,
                    func.count(),
                    func.bool_or(
                        and_(
                            GrammarAttempt.is_correct.is_(False),
                            GrammarAttempt.occurred_at >= now - POLICY.remediation_window,
                        )
                    ),
                )
                .where(
                    GrammarAttempt.user_id == user.id,
                    GrammarAttempt.unit_id.in_(unit_ids),
                    GrammarAttempt.mode == CHECK,
                )
                .group_by(GrammarAttempt.exercise_id)
            )
        ).all()
    }
    by_unit: dict[str, list[GrammarExercise]] = defaultdict(list)
    for e in exercises:
        by_unit[e.unit_id].append(e)
    plan: list[tuple[GrammarExercise, bool]] = []
    for uid in unit_ids:
        pool = by_unit.get(uid, [])
        rng.shuffle(pool)
        # Missed recently first (targeted), then the least asked, then random.
        pool.sort(key=lambda e: (not stats.get(e.id, (0, False))[1], stats.get(e.id, (0,))[0]))
        for e in pool[: POLICY.check_exercises_per_unit]:
            plan.append((e, bool(stats.get(e.id, (0, False))[1])))
    if not plan:
        return None
    rng.shuffle(plan)
    return await _create(db, user, language, CHECK, None, plan)


def next_pending(session: GrammarSession) -> GrammarSessionItem | None:
    return next((i for i in session.items if i.status == "pending"), None)


def _summary(s: GrammarSession) -> dict:
    items = s.items
    return {
        "total": len(items),
        "done": sum(i.status == "done" for i in items),
        "revealed": sum(i.status == "revealed" for i in items),
        "skipped": sum(i.status == "pending" for i in items),
        "first_try_correct": sum(bool(i.first_try_correct) for i in items),
        "remediation": sum(i.is_remediation for i in items),
    }


async def complete(
    db: AsyncSession, user: User, session_id: uuid.UUID, now: datetime
) -> GrammarSession:
    s = await get_session(db, user, session_id)
    if s.status != "active":
        return s
    s.summary = _summary(s)
    if s.mode == LEARN and s.unit_id:
        await _mark_studied(db, user, s.unit_id, now)
    s.status = "completed"
    s.completed_at = now
    await db.flush()
    return s


async def _progress_row(db: AsyncSession, user: User, unit_id: str) -> UserGrammarProgress:
    await db.execute(
        pg_insert(UserGrammarProgress)
        .values(user_id=user.id, unit_id=unit_id, policy_version=POLICY.version)
        .on_conflict_do_nothing()
    )
    return (
        await db.execute(
            select(UserGrammarProgress)
            .where(UserGrammarProgress.user_id == user.id, UserGrammarProgress.unit_id == unit_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _mark_studied(db: AsyncSession, user: User, unit_id: str, now: datetime) -> None:
    p = await _progress_row(db, user, unit_id)
    if p.studied_at is None:
        p.studied_at = now
        p.state = ProgressState.LEARNING
        p.next_review_at = next_local_midnight(user, now)
    p.policy_version = POLICY.version


# ---------------------------------------------------------------- answers


async def _lock_item(db: AsyncSession, user: User, item_id: uuid.UUID) -> GrammarSessionItem:
    item = (
        await db.execute(
            select(GrammarSessionItem)
            .join(GrammarSession, GrammarSession.id == GrammarSessionItem.session_id)
            .where(GrammarSessionItem.id == item_id, GrammarSession.user_id == user.id)
            .options(
                selectinload(GrammarSessionItem.exercise).selectinload(GrammarExercise.unit),
                selectinload(GrammarSessionItem.session),
            )
            .with_for_update(of=GrammarSessionItem)
        )
    ).scalar_one_or_none()
    if item is None:
        raise LearningError("task_not_found", 404)
    await db.refresh(item, ["status", "attempts", "first_try_correct"])
    if item.session.status != "active":
        raise LearningError("session_closed")
    return item


async def _replay(db: AsyncSession, user: User, key: str) -> dict | None:
    return (
        await db.execute(
            select(GrammarAttempt.result).where(
                GrammarAttempt.user_id == user.id, GrammarAttempt.idempotency_key == key
            )
        )
    ).scalar_one_or_none()


def correct_sentence(ex: GrammarExercise) -> str:
    """The full right answer as a sentence (a gap/choice shows the filled-in prompt)."""
    if ex.kind in (ExerciseKind.CHOICE, ExerciseKind.GAP):
        return blank(ex.payload["prompt"], ex.answers[0])
    return ex.answers[0]


async def submit(
    db: AsyncSession,
    user: User,
    item_id: uuid.UUID,
    *,
    idempotency_key: str,
    now: datetime,
    choice: int | None = None,
    text: str | None = None,
    reveal: bool = False,
) -> dict:
    """Grade one attempt (or a reveal). Duplicate keys replay the stored result.

    learn: retry until right; a wrong answer shows the answer and the explanation; never evidence.
    check: the first attempt closes the exercise; correct is evidence for the unit.
    """
    if (cached := await _replay(db, user, idempotency_key)) is not None:
        return cached
    item = await _lock_item(db, user, item_id)
    if (cached := await _replay(db, user, idempotency_key)) is not None:
        return cached
    if item.status != "pending":
        raise LearningError("task_closed")
    ex = item.exercise
    kind = ExerciseKind(ex.kind)
    language = item.session.language
    if reveal:
        correct, verdict, note, error, answer = False, "revealed", None, None, ""
    else:
        picked = None
        if kind == ExerciseKind.CHOICE:
            options = ex.payload["options"]
            if choice is None or not 0 <= choice < len(options):
                raise LearningError("invalid_choice", 422)
            picked = options[choice]
        elif text is None or not text.strip():
            raise LearningError("text_required", 422)
        g = grade(
            language,
            kind,
            ex.answers,
            text=text,
            choice=picked,
            case_sensitive_target=ex.payload.get("direction") != "target-cs",
        )
        correct, verdict, note = g.correct, g.verdict, g.note
        error = g.error.value if g.error else None
        answer = picked if picked is not None else (text or "")

    checking = item.session.mode == CHECK
    item.attempts += 1
    first = item.attempts == 1
    evidence = checking and correct and first and not reveal
    if first:
        item.first_try_correct = correct and not reveal
    if correct and not reveal:
        item.status = "done"
    elif reveal or checking:
        item.status = "revealed"
    done = item.status != "pending"
    show = done or not checking
    result = {
        "item_id": str(item.id),
        "correct": correct,
        "verdict": verdict,
        "note": note,
        "error": error,
        "counted": evidence,
        "attempts": item.attempts,
        "task_done": done,
        "can_retry": not done,
        "expected": ex.answers[0] if show else None,
        "solution": correct_sentence(ex) if show else None,
        "explanation": ex.explain if show else None,
        "unit_id": ex.unit_id,
        "unit_title": ex.unit.title,
    }
    tz = ZoneInfo(user.timezone)
    db.add(
        GrammarAttempt(
            user_id=user.id,
            exercise_id=ex.id,
            unit_id=ex.unit_id,
            session_id=item.session_id,
            item_id=item.id,
            mode=item.session.mode,
            attempt_no=item.attempts,
            answer=answer[:500],
            is_correct=correct,
            verdict=verdict,
            error_tag=error,
            revealed=reveal,
            counts_as_evidence=evidence,
            policy_version=POLICY.version,
            idempotency_key=idempotency_key,
            occurred_at=now,
            local_date=now.astimezone(tz).date(),
            result=result,
        )
    )
    try:
        async with db.begin_nested():
            await db.flush()
    except IntegrityError:
        await db.rollback()
        if (cached := await _replay(db, user, idempotency_key)) is not None:
            return cached
        raise
    if checking and first:
        await _apply(db, user, ex.unit_id, now, evidence=evidence)
    return result


async def _apply(db: AsyncSession, user: User, unit_id: str, now: datetime, *, evidence: bool):
    p = await _progress_row(db, user, unit_id)
    p.last_reviewed_at = now
    if evidence:
        p.correct_count += 1
        p.last_error_free_at = now
        p.review_streak += 1
        idx = min(p.review_streak, len(POLICY.review_intervals)) - 1
        p.next_review_at = now + POLICY.review_intervals[idx]
        a = GrammarAttempt
        n, days = (
            await db.execute(
                select(func.count(), func.count(func.distinct(a.local_date))).where(
                    a.user_id == user.id, a.unit_id == unit_id, a.counts_as_evidence.is_(True)
                )
            )
        ).one()
        if p.known_since_at is None:
            if n >= POLICY.known_required_correct and days >= POLICY.known_required_days:
                p.known_since_at = now
        elif now - p.known_since_at >= POLICY.mastery_delay:
            p.state = ProgressState.MASTERED
    else:
        p.error_count += 1
        p.review_streak = 0
        p.last_error_at = now
        p.next_review_at = next_local_midnight(user, now)
    p.policy_version = POLICY.version


# ---------------------------------------------------------------- maintenance


async def decay_sweep(db: AsyncSession, now: datetime) -> int:
    """>30 days without an error-free check: the unit is due again. Idempotent, as for words."""
    p = UserGrammarProgress
    result = await db.execute(
        update(p)
        .where(
            p.last_error_free_at.is_not(None),
            p.last_error_free_at < now - POLICY.decay_after,
            (p.last_decay_at.is_(None)) | (p.last_decay_at < p.last_error_free_at),
        )
        .values(
            state=case((p.state == ProgressState.MASTERED, ProgressState.LEARNING), else_=p.state),
            next_review_at=func.least(func.coalesce(p.next_review_at, now), now),
            review_streak=0,
            last_decay_at=now,
        )
    )
    return result.rowcount or 0


def recommended(units: list[UnitStatus]) -> str | None:
    """The first unit in curriculum order that was not studied yet."""
    return next((u.unit.id for u in units if u.status == "new"), None)
