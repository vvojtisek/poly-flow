"""CEFR placement diagnostic (rozřazovací test, part 2): sessions, answers, result, unlocks.

Graded like a test (one attempt, no hints, "Nevím" instead of guessing), adaptive per answer
(`app.domain.diagnostic`). Callers own the transaction.

Finishing records the band (`cefr_placements`) and unlocks curriculum nodes the way the
vocabulary part does: nothing becomes known by assumption.

- Grammar units at or below the band skip their lesson and wait in Ověření gramatiky
  (`studied_by='placement'`, due now). A check confirms them or sends the learner back to the
  lesson; a retake that places lower returns unconfirmed units above the new band to "new".
- The vocabulary level exams for bands at or below the result open without the 80 % known-words
  gate (they are still taken in order and still need the words in the lexicon).
"""

import json
import random
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.domain.diagnostic import (
    BANDS,
    DIAGNOSTIC,
    Item,
    ItemBank,
    Skill,
    band_at_most,
    band_label,
    choose_item,
    is_finished,
    next_band,
    posterior,
    prior_mean_from_vocabulary,
    result,
)
from app.domain.enums import CefrLevel, ContentFlag, Language, ProgressState
from app.models import CefrPlacement, DiagnosticSession, GrammarUnit, User, UserGrammarProgress
from app.services import placement as vocab_placement
from app.services.grammar import POLICY as GRAMMAR_POLICY
from app.services.learning import LearningError, wants_profanity

ACTIVE, COMPLETED, ABANDONED = "active", "completed", "abandoned"
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "diagnostic"


@lru_cache
def bank(language: Language) -> ItemBank | None:
    path = DATA_DIR / f"{Language(language).value}.diagnostic.json"
    if not path.exists():
        return None
    return ItemBank.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _suitable(user: User, item: Item) -> bool:
    flags = set(item.content_flags)
    if user.is_child:
        return not flags
    return wants_profanity(user) or ContentFlag.PROFANITY not in flags


def _pool(user: User, b: ItemBank, with_listening: bool) -> list[Item]:
    return [
        i for i in b.items if _suitable(user, i) and (with_listening or i.skill != Skill.LISTENING)
    ]


def _require_bank(language: Language) -> ItemBank:
    b = bank(language)
    if b is None:
        raise LearningError("diagnostic_unavailable", 404)
    return b


async def get_active(db: AsyncSession, user: User, language: Language) -> DiagnosticSession | None:
    return (
        await db.execute(
            select(DiagnosticSession).where(
                DiagnosticSession.user_id == user.id,
                DiagnosticSession.language == language,
                DiagnosticSession.status == ACTIVE,
            )
        )
    ).scalar_one_or_none()


async def get_session(
    db: AsyncSession, user: User, session_id: uuid.UUID, *, lock: bool = False
) -> DiagnosticSession:
    q = select(DiagnosticSession).where(
        DiagnosticSession.id == session_id, DiagnosticSession.user_id == user.id
    )
    if lock:
        q = q.with_for_update().execution_options(populate_existing=True)
    s = (await db.execute(q)).scalar_one_or_none()
    if s is None:  # someone else's session looks exactly like a missing one
        raise LearningError("session_not_found", 404)
    return s


async def latest(db: AsyncSession, user: User, language: Language) -> CefrPlacement | None:
    return await db.get(CefrPlacement, (user.id, language))


async def start(
    db: AsyncSession,
    user: User,
    language: Language,
    *,
    with_listening: bool,
    now: datetime,
) -> DiagnosticSession:
    """Resume the open diagnostic in this language, or start one."""
    existing = await get_active(db, user, language)
    if existing is not None:
        return existing
    b = _require_bank(language)
    vocab = await vocab_placement.get_placement(db, user, language)
    vocab_level = vocab.level if vocab and vocab.status == vocab_placement.PLACED else None
    s = DiagnosticSession(
        user_id=user.id,
        language=language,
        status=ACTIVE,
        policy_version=DIAGNOSTIC.version,
        bank_revision=b.revision,
        prior_mean=prior_mean_from_vocabulary(vocab_level),
        with_listening=with_listening,
        items=[],
        result={},
    )
    db.add(s)
    await db.flush()
    return s


def _answered(s: DiagnosticSession, by_id: dict[str, Item]) -> list[tuple[Item, bool | None]]:
    return [
        (by_id[e["id"]], e["correct"]) for e in s.items if e.get("answered") and e["id"] in by_id
    ]


def pending(s: DiagnosticSession) -> tuple[int, dict] | None:
    if s.items and not s.items[-1].get("answered"):
        return len(s.items) - 1, s.items[-1]
    return None


def _stage(s: DiagnosticSession, by_id: dict[str, Item]) -> dict:
    answered = _answered(s, by_id)
    post = posterior([(i.difficulty, c) for i, c in answered], s.prior_mean)
    return {"asked": len(answered), "max_items": DIAGNOSTIC.max_items, "theta": round(post.mean, 2)}


async def advance(
    db: AsyncSession, user: User, s: DiagnosticSession, rng: random.Random
) -> tuple[int, Item, list[str]] | None:
    """The pending question (adding the next one when needed), or None when the test is done."""
    b = _require_bank(s.language)
    by_id = b.by_id()
    p = pending(s)
    if p is not None and p[1]["id"] in by_id:
        return p[0], by_id[p[1]["id"]], p[1]["options"]
    answered = _answered(s, by_id)
    asked_ids = {e["id"] for e in s.items}
    left = [i for i in _pool(user, b, s.with_listening) if i.id not in asked_ids]
    post = posterior([(i.difficulty, c) for i, c in answered], s.prior_mean)
    if is_finished(post, len(answered), len(left)):
        return None
    item = choose_item(left, [i.skill for i, _ in answered], post.mean, rng)
    if item is None:
        return None
    options = list(item.options)
    rng.shuffle(options)
    s.items = [
        *s.items,
        {"id": item.id, "options": options, "choice": None, "correct": None, "answered": False},
    ]
    flag_modified(s, "items")
    await db.flush()
    return len(s.items) - 1, item, options


def question_out(s: DiagnosticSession, position: int, item: Item, options: list[str]) -> dict:
    by_id = _require_bank(s.language).by_id()
    return {
        "position": position,
        "skill": item.skill.value,
        "band": band_label(item.level),
        "prompt": item.prompt,
        "context": item.context,
        "has_audio": item.audio is not None,
        "options": options,
        **_stage(s, by_id),
    }


async def answer(
    db: AsyncSession,
    user: User,
    session_id: uuid.UUID,
    position: int,
    choice: str | None,
    now: datetime,
) -> dict:
    """Grade the pending question once; a repeated submission replays the stored verdict."""
    s = await get_session(db, user, session_id, lock=True)
    by_id = _require_bank(s.language).by_id()
    if position < 0 or position >= len(s.items):
        raise LearningError("question_not_found", 404)
    entry = s.items[position]
    item = by_id.get(entry["id"])
    if item is None:
        raise LearningError("question_not_found", 404)
    if not entry.get("answered"):
        if s.status != ACTIVE:
            raise LearningError("session_closed", 409)
        if choice is not None and choice not in entry["options"]:
            raise LearningError("invalid_choice", 422)
        entry = {**entry, "choice": choice, "correct": choice == item.answer, "answered": True}
        s.items = [*s.items[:position], entry, *s.items[position + 1 :]]
        flag_modified(s, "items")
        await db.flush()
    return {
        "position": position,
        "correct": bool(entry["correct"]),
        "dont_know": entry["choice"] is None,
        "answer": item.answer,
        "explain": item.explain,
        "transcript": item.audio,  # listening: shown once answered
        **_stage(s, by_id),
    }


async def finish(db: AsyncSession, user: User, s: DiagnosticSession, now: datetime) -> dict:
    """Close the test, record the band and unlock curriculum nodes. Idempotent per session."""
    if s.status == COMPLETED:
        return s.result
    by_id = _require_bank(s.language).by_id()
    answered = _answered(s, by_id)
    if len(answered) < DIAGNOSTIC.min_items:
        # Stopped early: too little to place; nothing changes.
        s.status, s.completed_at = ABANDONED, now
        s.result = {"placed": False, "asked": len(answered)}
        return s.result
    r = result(answered, s.prior_mean)
    queued, returned = await _unlock_grammar(db, user, s.language, r.level, now)
    s.result = {
        "placed": True,
        "level": band_label(r.level),
        "cefr": r.level.value if r.level else None,
        "next": band_label(next_band(r.level)) if next_band(r.level) else None,
        "low": band_label(r.low_level),
        "high": band_label(r.high_level),
        "theta": round(r.theta, 3),
        "sd": round(r.sd, 3),
        "asked": r.asked,
        "correct": r.correct,
        "skills": [
            {
                "skill": k.skill.value,
                "asked": k.asked,
                "correct": k.correct,
                "expected": round(k.expected, 2),
                "verdict": k.verdict,
            }
            for k in r.skills
        ],
        "bands": [
            {
                "band": band_label(b),
                "correct": r.bands[band_label(b)][0],
                "asked": r.bands[band_label(b)][1],
            }
            for b in BANDS
            if band_label(b) in r.bands
        ],
        "grammar_queued": queued,
        "grammar_returned": returned,
        "exams_opened": [b.value for b in BANDS[:4] if band_at_most(b, r.level)],
    }
    s.status, s.completed_at = COMPLETED, now
    values = {
        "level": r.level,
        "theta": r.theta,
        "theta_sd": r.sd,
        "session_id": s.id,
        "decided_at": now,
        "policy_version": DIAGNOSTIC.version,
    }
    await db.execute(
        pg_insert(CefrPlacement)
        .values(user_id=user.id, language=s.language, **values)
        .on_conflict_do_update(index_elements=["user_id", "language"], set_=values)
    )
    await db.flush()
    return s.result


async def abandon(db: AsyncSession, user: User, session_id: uuid.UUID, now: datetime) -> dict:
    """Stop now: places the learner if enough was answered, else closes without a result."""
    s = await get_session(db, user, session_id, lock=True)
    if s.status != ACTIVE:
        return s.result
    p = pending(s)
    if p is not None:  # drop the unanswered question
        s.items = s.items[:-1]
        flag_modified(s, "items")
    return await finish(db, user, s, now)


async def _unlock_grammar(
    db: AsyncSession, user: User, language: Language, level: CefrLevel | None, now: datetime
) -> tuple[int, int]:
    units = list(
        (
            await db.execute(
                select(GrammarUnit).where(
                    GrammarUnit.language == language, GrammarUnit.active.is_(True)
                )
            )
        ).scalars()
    )
    if not units:
        return 0, 0
    below = [u.id for u in units if u.level in BANDS and band_at_most(u.level, level)]
    above = [u.id for u in units if u.id not in set(below)]
    p = UserGrammarProgress
    returned = 0
    if above:
        res = await db.execute(
            update(p)
            .where(
                p.user_id == user.id,
                p.unit_id.in_(above),
                p.studied_by == "placement",
                p.last_reviewed_at.is_(None),
            )
            .values(studied_at=None, studied_by=None, next_review_at=None, state=ProgressState.NEW)
        )
        returned = res.rowcount or 0
    queued = 0
    if below:
        stmt = pg_insert(p).values(
            [
                {
                    "user_id": user.id,
                    "unit_id": uid,
                    "studied_at": now,
                    "studied_by": "placement",
                    "state": ProgressState.LEARNING,
                    "next_review_at": now,
                    "policy_version": GRAMMAR_POLICY.version,
                }
                for uid in below
            ]
        )
        res = await db.execute(
            stmt.on_conflict_do_update(
                index_elements=["user_id", "unit_id"],
                set_={
                    "studied_at": now,
                    "studied_by": "placement",
                    "state": ProgressState.LEARNING,
                    "next_review_at": now,
                },
                where=and_(p.studied_at.is_(None)),
            )
        )
        queued = res.rowcount or 0
    return queued, returned


def audio_text(s: DiagnosticSession, position: int) -> str:
    by_id = _require_bank(s.language).by_id()
    if position < 0 or position >= len(s.items):
        raise LearningError("question_not_found", 404)
    item = by_id.get(s.items[position]["id"])
    if item is None or item.audio is None:
        raise LearningError("no_audio", 404)
    return item.audio
