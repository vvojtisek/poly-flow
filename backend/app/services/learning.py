"""Lesson engine (plan P2, policy v2). Callers own the transaction; `now` is injected.

Two separate modes:
- learn (Lekce): a scene introduces the words in context, then guided practice with free hints
  and retries. Nothing here counts toward knowing a word; completing it introduces the words.
- check (Ověření): introduced words that are due, from the day after their lesson. One attempt,
  no hints. The only source of knowledge evidence.
"""

import math
import random
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, select, true, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.domain.enums import GRAMMAR_GATE_WORDS, Language, ProgressState
from app.domain.learning_policy import POLICY, next_review_interval, smooth
from app.domain.orthography import check_spelling
from app.models import (
    AuthSession,
    GrammarUnlock,
    LearningEvent,
    LearningSession,
    LearningTask,
    LexiconItem,
    Scene,
    SceneWord,
    User,
    UserWordProgress,
)
from app.models.learning import SessionMode, SessionStatus, TaskStatus, TaskType

MAX_RECOGNITION_OPTIONS = 4
MAX_HINT_LEVEL = 2


class LearningError(Exception):
    def __init__(self, code: str, status: int = 409) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


# ---------------------------------------------------------------- sessions


def _with_tasks():
    return (
        selectinload(LearningSession.tasks).selectinload(LearningTask.item),
        selectinload(LearningSession.scene),
    )


def next_local_midnight(user: User, now: datetime) -> datetime:
    """Start of the profile's next local day: when freshly learned words become checkable."""
    tz = ZoneInfo(user.timezone)
    tomorrow = now.astimezone(tz).date() + timedelta(days=1)
    return datetime.combine(tomorrow, time(0), tzinfo=tz).astimezone(UTC)


async def get_active_session(
    db: AsyncSession, user: User, language: Language, mode: SessionMode = SessionMode.LEARN
) -> LearningSession | None:
    return (
        await db.execute(
            select(LearningSession)
            .where(
                LearningSession.user_id == user.id,
                LearningSession.language == language,
                LearningSession.mode == mode,
                LearningSession.status == SessionStatus.ACTIVE,
            )
            .options(*_with_tasks())
        )
    ).scalar_one_or_none()


async def get_session(db: AsyncSession, user: User, session_id: uuid.UUID) -> LearningSession:
    s = (
        await db.execute(
            select(LearningSession)
            .where(LearningSession.id == session_id, LearningSession.user_id == user.id)
            .options(*_with_tasks())
        )
    ).scalar_one_or_none()
    if s is None:
        raise LearningError("session_not_found", 404)
    return s


def _suitable(user: User):
    """Age-appropriate filter: child profiles never get a flagged item, in any role."""
    return func.cardinality(LexiconItem.content_flags) == 0 if user.is_child else true()


@dataclass(slots=True)
class _Planned:
    item: LexiconItem
    task_type: TaskType
    is_new: bool


def _not_introduced(user: User):
    """Outer-join condition + filter for words this profile has not been introduced to."""
    return (
        and_(
            UserWordProgress.lexicon_item_id == LexiconItem.id,
            UserWordProgress.user_id == user.id,
        ),
        UserWordProgress.introduced_at.is_(None),
    )


async def _plan_learn(
    db: AsyncSession, user: User, language: Language
) -> tuple[Scene | None, list[_Planned]]:
    """The next scene with words not yet introduced, and up to N of those words.

    Scenes are walked in curriculum order; a scene with more new words than fit in one lesson
    opens the next lesson too. Words without a scene follow by frequency, with their example
    sentence as the context.
    """
    on, still_new = _not_introduced(user)
    limit = POLICY.new_items_per_session
    scene_ok = true()
    if user.is_child:
        # A scene that introduces a flagged word is skipped as a whole, not shown without it.
        flagged = aliased(LexiconItem)
        scene_ok = ~(
            select(SceneWord.scene_id)
            .join(flagged, flagged.id == SceneWord.lexicon_item_id)
            .where(SceneWord.scene_id == Scene.id, func.cardinality(flagged.content_flags) > 0)
            .exists()
        )
    rows = (
        await db.execute(
            select(Scene, LexiconItem)
            .join(SceneWord, SceneWord.scene_id == Scene.id)
            .join(LexiconItem, LexiconItem.id == SceneWord.lexicon_item_id)
            .outerjoin(UserWordProgress, on)
            .where(Scene.language == language, still_new, scene_ok)
            .order_by(Scene.position, SceneWord.position)
            .limit(limit)
        )
    ).all()
    scene: Scene | None = None
    items: list[LexiconItem]
    if rows:
        scene = rows[0][0]
        items = [item for sc, item in rows if sc.id == scene.id]
    else:
        items = list(
            (
                await db.execute(
                    select(LexiconItem)
                    .outerjoin(UserWordProgress, on)
                    .where(LexiconItem.language == language, still_new, _suitable(user))
                    .order_by(LexiconItem.frequency_rank)
                    .limit(limit)
                )
            ).scalars()
        )
    # Meet the word first (recognition), produce it later in the same lesson (recall).
    plan = [_Planned(i, TaskType.RECOGNITION, True) for i in items]
    plan += [_Planned(i, TaskType.RECALL, True) for i in items]
    return scene, plan


async def _plan_check(
    db: AsyncSession, user: User, language: Language, now: datetime
) -> list[_Planned]:
    due_rows = (
        await db.execute(
            select(UserWordProgress, LexiconItem)
            .join(LexiconItem, LexiconItem.id == UserWordProgress.lexicon_item_id)
            .where(
                UserWordProgress.user_id == user.id,
                LexiconItem.language == language,
                UserWordProgress.introduced_at.is_not(None),
                UserWordProgress.next_review_at <= now,
                _suitable(user),
            )
            .order_by(UserWordProgress.next_review_at, LexiconItem.frequency_rank)
            .limit(POLICY.session_max_tasks)
        )
    ).all()
    # Recognition until the word is passively known, then production.
    return [
        _Planned(item, TaskType.RECALL if p.passive_known else TaskType.RECOGNITION, False)
        for p, item in due_rows
    ]


async def _recognition_payload(
    db: AsyncSession, user: User, item: LexiconItem, rng: random.Random
) -> dict | None:
    candidates = (
        await db.execute(
            select(LexiconItem.translation_cs)
            .where(
                LexiconItem.language == item.language,
                LexiconItem.id != item.id,
                LexiconItem.translation_cs != item.translation_cs,
                _suitable(user),
            )
            .order_by(func.abs(LexiconItem.frequency_rank - item.frequency_rank))
            .limit(12)
        )
    ).scalars()
    distractors = list(dict.fromkeys(candidates))  # dedupe, keep order
    if not distractors:
        return None
    picked = rng.sample(distractors, min(MAX_RECOGNITION_OPTIONS - 1, len(distractors)))
    options = [item.translation_cs, *picked]
    rng.shuffle(options)
    return {"options": options, "correct": options.index(item.translation_cs)}


async def start_session(
    db: AsyncSession,
    user: User,
    language: Language,
    now: datetime,
    rng: random.Random | None = None,
    mode: SessionMode = SessionMode.LEARN,
) -> LearningSession | None:
    """Resume the open lesson/check for this language, or build a new one. None = nothing to do."""
    existing = await get_active_session(db, user, language, mode)
    if existing is not None:
        return existing
    rng = rng or random.Random()
    scene: Scene | None = None
    if mode == SessionMode.LEARN:
        scene, plan = await _plan_learn(db, user, language)
    else:
        plan = await _plan_check(db, user, language, now)
    if not plan:
        return None

    session = LearningSession(
        user_id=user.id,
        language=language,
        mode=mode,
        scene_id=scene.id if scene else None,
        policy_version=POLICY.version,
        summary={},
    )
    try:
        async with db.begin_nested():
            db.add(session)
            await db.flush()
    except IntegrityError:
        # A concurrent request opened the session first; resume that one.
        return await get_active_session(db, user, language, mode)

    position = 0
    for p in plan:
        payload: dict = {}
        task_type = p.task_type
        if task_type == TaskType.RECOGNITION:
            payload = await _recognition_payload(db, user, p.item, rng) or {}
            if not payload:
                task_type = TaskType.RECALL  # no distractors available
        db.add(
            LearningTask(
                session_id=session.id,
                lexicon_item_id=p.item.id,
                position=position,
                task_type=task_type,
                is_new_item=p.is_new,
                payload=payload,
            )
        )
        position += 1
    await db.flush()
    db.expire(session, ["tasks"])
    return await get_session(db, user, session.id)


def next_pending(session: LearningSession) -> LearningTask | None:
    return next((t for t in session.tasks if t.status == TaskStatus.PENDING), None)


async def mark_seen(db: AsyncSession, user: User, item: LexiconItem, now: datetime) -> None:
    """Exposure only: records last_seen_at, never knowledge."""
    stmt = pg_insert(UserWordProgress).values(
        id=uuid.uuid4(),
        user_id=user.id,
        lexicon_item_id=item.id,
        state=ProgressState.NEW,
        first_seen_at=now,
        last_seen_at=now,
        policy_version=POLICY.version,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_user_word_progress_user_item",
        set_={
            "last_seen_at": now,
            "first_seen_at": func.coalesce(UserWordProgress.first_seen_at, now),
        },
    )
    await db.execute(stmt)


# ---------------------------------------------------------------- tasks


async def _lock_task(db: AsyncSession, user: User, task_id: uuid.UUID) -> LearningTask:
    task = (
        await db.execute(
            select(LearningTask)
            .join(LearningSession, LearningSession.id == LearningTask.session_id)
            .where(LearningTask.id == task_id, LearningSession.user_id == user.id)
            .options(selectinload(LearningTask.item), selectinload(LearningTask.session))
            .with_for_update(of=LearningTask)
        )
    ).scalar_one_or_none()
    if task is None:
        raise LearningError("task_not_found", 404)
    await db.refresh(task, ["status", "attempts", "hint_level", "first_try_correct"])
    if task.session.status != SessionStatus.ACTIVE:
        raise LearningError("session_closed")
    return task


async def _replay(db: AsyncSession, user: User, key: str) -> dict | None:
    return (
        await db.execute(
            select(LearningEvent.result).where(
                LearningEvent.user_id == user.id, LearningEvent.idempotency_key == key
            )
        )
    ).scalar_one_or_none()


def hint_text(task: LearningTask) -> str | None:
    if task.hint_level == 0 or task.task_type != TaskType.RECALL:
        return None
    lemma = task.item.lemma
    shown = 1 if task.hint_level == 1 else max(1, math.ceil(len(lemma) / 2))
    return lemma[:shown] + "…"


def cloze(task: LearningTask) -> str | None:
    """Example sentence with the lemma blanked (whole word, case-insensitive), if present."""
    item = task.item
    if task.task_type != TaskType.RECALL or not item.example_sentence:
        return None
    pattern = re.compile(rf"(?<!\w){re.escape(item.lemma)}(?!\w)", re.IGNORECASE)
    blanked, n = pattern.subn("___", item.example_sentence, count=1)
    return blanked if n else None


def visible_options(task: LearningTask) -> list[tuple[int, str]] | None:
    """Recognition options; a hint removes two wrong ones (indices stay stable)."""
    if task.task_type != TaskType.RECOGNITION:
        return None
    options = list(enumerate(task.payload["options"]))
    if task.hint_level > 0:
        correct = task.payload["correct"]
        wrong = [i for i, _ in options if i != correct][2:]
        options = [(i, o) for i, o in options if i == correct or i in wrong]
    return options


# ---------------------------------------------------------------- audio


def spoken_word(item: LexiconItem) -> str:
    """The word as the learner sees it: German nouns with their article (der Hund)."""
    if item.language == Language.DE and item.gender in {"der", "die", "das"}:
        return f"{item.gender} {item.lemma}"
    return item.lemma


async def get_task(db: AsyncSession, user: User, task_id: uuid.UUID) -> LearningTask:
    task = (
        await db.execute(
            select(LearningTask)
            .join(LearningSession, LearningSession.id == LearningTask.session_id)
            .where(LearningTask.id == task_id, LearningSession.user_id == user.id)
            .options(selectinload(LearningTask.item))
        )
    ).scalar_one_or_none()
    if task is None:
        raise LearningError("task_not_found", 404)
    return task


def task_audio_text(task: LearningTask, part: str) -> str:
    """Text the learner may hear for a task: only what the task already shows.

    A pending recall task asks the learner to produce the word, so its audio waits until the
    task is finished (then it plays the expected answer).
    """
    if task.task_type == TaskType.RECALL and task.status == TaskStatus.PENDING:
        raise LearningError("audio_would_reveal")
    if part == "word":
        return spoken_word(task.item)
    if task.item.example_sentence:
        return task.item.example_sentence
    raise LearningError("audio_not_found", 404)


def session_audio_text(
    session: LearningSession, line: int | None, item_id: uuid.UUID | None, part: str
) -> str:
    """Text of a scene line or a word card of a lesson, as `SessionOut` presents them."""
    if session.mode != SessionMode.LEARN:
        raise LearningError("audio_not_found", 404)
    lines = session.scene.lines if session.scene else []
    if line is not None:
        if line >= len(lines):
            raise LearningError("audio_not_found", 404)
        return "".join(seg["t"] for seg in lines[line]["segments"])
    item = next(
        (t.item for t in session.tasks if t.lexicon_item_id == item_id and t.is_new_item), None
    )
    if item is None:
        raise LearningError("audio_not_found", 404)
    if part == "word":
        return spoken_word(item)
    for scene_line in lines:  # the card's context: the scene line with the word, else example
        if any(seg.get("item") == str(item.id) for seg in scene_line["segments"]):
            return "".join(seg["t"] for seg in scene_line["segments"])
    if item.example_sentence:
        return item.example_sentence
    raise LearningError("audio_not_found", 404)


async def use_hint(db: AsyncSession, user: User, task_id: uuid.UUID) -> LearningTask:
    task = await _lock_task(db, user, task_id)
    if task.status != TaskStatus.PENDING:
        raise LearningError("task_closed")
    if task.session.mode == SessionMode.CHECK:
        raise LearningError("hints_disabled")
    limit = 1 if task.task_type == TaskType.RECOGNITION else MAX_HINT_LEVEL
    task.hint_level = min(task.hint_level + 1, limit)
    return task


def _expected(task: LearningTask) -> str:
    item = task.item
    return item.translation_cs if task.task_type == TaskType.RECOGNITION else item.lemma


async def submit_answer(
    db: AsyncSession,
    user: User,
    task_id: uuid.UUID,
    *,
    idempotency_key: str,
    now: datetime,
    choice: int | None = None,
    text: str | None = None,
    reveal: bool = False,
) -> dict:
    """Grade one attempt (or a reveal) and aggregate progress. Duplicate keys replay.

    learn: retry until correct; a wrong answer shows the right one; never evidence.
    check: the first attempt closes the task; correct and hint-free is evidence.
    """
    if (cached := await _replay(db, user, idempotency_key)) is not None:
        return cached
    task = await _lock_task(db, user, task_id)
    if (cached := await _replay(db, user, idempotency_key)) is not None:
        return cached  # a concurrent duplicate committed while we waited for the lock
    if task.status != TaskStatus.PENDING:
        raise LearningError("task_closed")

    item = task.item
    note = None
    ortho = None
    if reveal:
        correct, verdict, answer = False, "revealed", ""
    elif task.task_type == TaskType.RECOGNITION:
        options = task.payload["options"]
        if choice is None or not 0 <= choice < len(options):
            raise LearningError("invalid_choice", 422)
        correct = choice == task.payload["correct"]
        verdict = "exact" if correct else "wrong"
        answer = options[choice]
    else:
        if text is None:
            raise LearningError("text_required", 422)
        res = check_spelling(item.language, item.lemma, text, item.pos)
        correct, verdict, note, ortho, answer = (
            res.correct,
            res.verdict.value,
            res.note,
            res.score,
            text,
        )

    checking = task.session.mode == SessionMode.CHECK
    task.attempts += 1
    first_attempt = task.attempts == 1
    hint_used = task.hint_level > 0
    evidence = checking and correct and first_attempt and not hint_used and not reveal
    if first_attempt:
        task.first_try_correct = correct and not hint_used and not reveal
    if correct and not reveal:
        task.status = TaskStatus.DONE
    elif reveal or checking:
        task.status = TaskStatus.REVEALED  # closed without a correct answer
    done = task.status != TaskStatus.PENDING
    # learn: show the right answer straight away, then the learner tries again.
    show = done or not checking

    result = {
        "task_id": str(task.id),
        "correct": correct,
        "verdict": verdict,
        "note": note,
        "counted": evidence,
        "attempts": task.attempts,
        "task_done": done,
        "can_retry": not done,
        # check: show the answer only once it can no longer be guessed from it.
        "expected": _expected(task) if show else None,
        "meaning": item.translation_cs if show else None,
    }
    tz = ZoneInfo(user.timezone)
    db.add(
        LearningEvent(
            user_id=user.id,
            lexicon_item_id=item.id,
            session_id=task.session_id,
            task_id=task.id,
            task_type=task.task_type,
            attempt_no=task.attempts,
            answer=answer[:500],
            is_correct=correct,
            verdict=verdict,
            hint_used=hint_used,
            revealed=reveal,
            counts_as_evidence=evidence,
            orthography_score=ortho,
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

    if checking:
        await _apply_progress(
            db,
            user,
            item,
            task.task_type,
            now=now,
            first_attempt=first_attempt,
            evidence=evidence,
            orthography=ortho if first_attempt else None,
        )
    else:
        await mark_seen(db, user, item, now)  # practice is exposure, not knowledge
    return result


async def _apply_progress(
    db: AsyncSession,
    user: User,
    item: LexiconItem,
    task_type: TaskType,
    *,
    now: datetime,
    first_attempt: bool,
    evidence: bool,
    orthography: float | None,
) -> None:
    await mark_seen(db, user, item, now)
    p = (
        await db.execute(
            select(UserWordProgress)
            .where(
                UserWordProgress.user_id == user.id,
                UserWordProgress.lexicon_item_id == item.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one()

    if p.state == ProgressState.NEW:
        p.state = ProgressState.LEARNING
    if first_attempt:
        p.last_reviewed_at = now
        if evidence:
            p.correct_count += 1
            p.last_error_free_at = now
            p.review_streak += 1
            p.next_review_at = now + next_review_interval(p.review_streak)
        else:
            p.error_count += 1
            p.review_streak = 0
            # Due again tomorrow: a same-day retry would measure short-term memory.
            p.next_review_at = next_local_midnight(user, now)
        if orthography is not None:
            p.orthography_score = smooth(p.orthography_score, orthography)

    if evidence:
        ev = LearningEvent
        base = and_(
            ev.user_id == user.id, ev.lexicon_item_id == item.id, ev.counts_as_evidence.is_(True)
        )
        recall = ev.task_type == TaskType.RECALL
        row = (
            await db.execute(
                select(
                    func.count(),
                    func.count(func.distinct(ev.local_date)),
                    func.count().filter(recall),
                    func.count(func.distinct(case((recall, ev.local_date)))),
                ).where(base)
            )
        ).one()
        all_n, all_days, recall_n, recall_days = row
        # Producing the word also demonstrates recognising it.
        if all_n >= POLICY.passive_required_correct and all_days >= POLICY.passive_required_days:
            p.passive_known = True
        if (
            recall_n >= POLICY.active_required_correct
            and recall_days >= POLICY.active_required_days
        ):
            p.active_known = True
        if p.passive_known and p.active_known:
            if p.known_since_at is None:
                p.known_since_at = now
                await _maybe_unlock_grammar(db, user, item.language, now)
            elif now - p.known_since_at >= POLICY.mastery_delay:
                p.state = ProgressState.MASTERED
    p.policy_version = POLICY.version


async def _maybe_unlock_grammar(
    db: AsyncSession, user: User, language: Language, now: datetime
) -> None:
    known = (
        await db.execute(
            select(func.count())
            .select_from(UserWordProgress)
            .join(LexiconItem, LexiconItem.id == UserWordProgress.lexicon_item_id)
            .where(
                UserWordProgress.user_id == user.id,
                LexiconItem.language == language,
                LexiconItem.frequency_rank <= GRAMMAR_GATE_WORDS,
                UserWordProgress.passive_known.is_(True),
                UserWordProgress.active_known.is_(True),
            )
        )
    ).scalar_one()
    if known >= GRAMMAR_GATE_WORDS:
        await db.execute(
            pg_insert(GrammarUnlock)
            .values(user_id=user.id, language=language, unlocked_at=now)
            .on_conflict_do_nothing()
        )


async def complete_session(
    db: AsyncSession, user: User, session_id: uuid.UUID, now: datetime
) -> LearningSession:
    s = await get_session(db, user, session_id)
    if s.status == SessionStatus.ACTIVE:
        tasks = s.tasks
        s.summary = {
            "total": len(tasks),
            "done": sum(t.status == TaskStatus.DONE for t in tasks),
            "revealed": sum(t.status == TaskStatus.REVEALED for t in tasks),
            "skipped": sum(t.status == TaskStatus.PENDING for t in tasks),
            "first_try_correct": sum(bool(t.first_try_correct) for t in tasks),
            "new_items": len({t.lexicon_item_id for t in tasks if t.is_new_item}),
            "reviewed_items": len({t.lexicon_item_id for t in tasks if not t.is_new_item}),
        }
        if s.mode == SessionMode.LEARN:
            await _introduce(db, user, [t.item for t in tasks if t.is_new_item], now)
        s.status = SessionStatus.COMPLETED
        s.completed_at = now
    return s


async def _introduce(db: AsyncSession, user: User, items: list[LexiconItem], now: datetime):
    """A finished lesson introduces its words: checkable from the next local day."""
    checkable = next_local_midnight(user, now)
    for item in {i.id: i for i in items}.values():
        await mark_seen(db, user, item, now)
        await db.execute(
            update(UserWordProgress)
            .where(
                UserWordProgress.user_id == user.id,
                UserWordProgress.lexicon_item_id == item.id,
                UserWordProgress.introduced_at.is_(None),
            )
            .values(
                introduced_at=now,
                state=case(
                    (UserWordProgress.state == ProgressState.NEW, ProgressState.LEARNING),
                    else_=UserWordProgress.state,
                ),
                next_review_at=checkable,
                policy_version=POLICY.version,
            )
        )


# ---------------------------------------------------------------- maintenance


async def decay_sweep(db: AsyncSession, now: datetime) -> int:
    """>30 days without a verified error-free use: back to priority review.

    Idempotent: a row is touched once per success (last_decay_at >= last_error_free_at
    afterwards). Measured scores are kept; effective retention is derived on read.
    """
    p = UserWordProgress
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


async def prune_expired_sessions(db: AsyncSession, now: datetime) -> int:
    from sqlalchemy import delete

    result = await db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    return result.rowcount or 0


# ---------------------------------------------------------------- overview


async def progress_overview(db: AsyncSession, user: User, language: Language, now: datetime):
    from app.domain.progression import MILESTONES
    from app.schemas.learning import BandProgress, ProgressOut

    p, li = UserWordProgress, LexiconItem
    known_expr = and_(p.passive_known.is_(True), p.active_known.is_(True))
    row = (
        await db.execute(
            select(
                func.count().filter(p.state != ProgressState.NEW),
                func.count().filter(p.passive_known.is_(True)),
                func.count().filter(p.active_known.is_(True)),
                func.count().filter(known_expr),
                func.count().filter(p.introduced_at.is_not(None)),
                func.count().filter(and_(p.introduced_at.is_not(None), p.next_review_at <= now)),
                func.avg(p.orthography_score),
                func.count(p.phonetic_score),
            )
            .select_from(p)
            .join(li, li.id == p.lexicon_item_id)
            .where(p.user_id == user.id, li.language == language)
        )
    ).one()
    seen, passive, active, known, introduced, due, ortho_avg, phonetic = row

    by_state = dict.fromkeys(ProgressState, 0)
    for state, n in (
        await db.execute(
            select(p.state, func.count())
            .join(li, li.id == p.lexicon_item_id)
            .where(p.user_id == user.id, li.language == language)
            .group_by(p.state)
        )
    ).all():
        by_state[state] = n

    bands = (
        await db.execute(
            select(
                li.frequency_band,
                func.count(li.id),
                func.count(p.id).filter(known_expr),
            )
            .outerjoin(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
            .where(li.language == language)
            .group_by(li.frequency_band)
            .order_by(li.frequency_band)
        )
    ).all()
    lexicon_items = sum(n for _, n, _ in bands)

    unlocked = (
        await db.execute(
            select(GrammarUnlock.user_id).where(
                GrammarUnlock.user_id == user.id, GrammarUnlock.language == language
            )
        )
    ).first() is not None
    nxt = next((m for m in MILESTONES if m.rank > known), None)
    open_lesson = await get_active_session(db, user, language, SessionMode.LEARN)
    open_check = await get_active_session(db, user, language, SessionMode.CHECK)
    return ProgressOut(
        language=language,
        lexicon_items=lexicon_items,
        seen=seen,
        by_state=by_state,
        passive_known=passive,
        active_known=active,
        known=known,
        introduced=introduced,
        due_now=due,
        orthography_avg=round(float(ortho_avg), 3) if ortho_avg is not None else None,
        phonetic_measured=phonetic,
        grammar_unlocked=unlocked,
        grammar_gate=GRAMMAR_GATE_WORDS,
        next_milestone=nxt.rank if nxt else None,
        next_milestone_cefr=nxt.cefr if nxt else None,
        by_band=[BandProgress(band=b, items=n, known=k) for b, n, k in bands],
        active_session_id=open_lesson.id if open_lesson else None,
        active_check_session_id=open_check.id if open_check else None,
    )
