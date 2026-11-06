"""Review of a finished session: each word, the first answer, and where the word stands now.

Read-only over the session's tasks, its first-attempt events and the profile's progress rows.
The learner's own answers are shown back only to the learner (session ownership is checked).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LearningEvent, User, UserWordProgress
from app.models.learning import SessionStatus, TaskType
from app.services import notes
from app.services.learning import LearningError, get_session


@dataclass(slots=True)
class ReviewItem:
    item_id: uuid.UUID
    lemma: str
    gender: str | None
    translation: str
    task: str
    first_try: bool | None  # None: not answered (skipped)
    answered: str | None  # the first answer as typed or chosen
    expected: str
    error: str | None
    passive_known: bool
    active_known: bool
    next_review_at: datetime | None
    note: str | None


async def session_review(
    db: AsyncSession, user: User, session_id: uuid.UUID
) -> tuple[str, list[ReviewItem]]:
    s = await get_session(db, user, session_id)
    if s.status != SessionStatus.COMPLETED:
        raise LearningError("session_not_finished", 409)
    tasks = sorted(s.tasks, key=lambda t: t.position)
    first = {
        e.task_id: e
        for e in (
            await db.execute(
                select(LearningEvent).where(
                    LearningEvent.session_id == s.id, LearningEvent.attempt_no == 1
                )
            )
        ).scalars()
    }
    item_ids = list({t.lexicon_item_id for t in tasks})
    progress = {
        p.lexicon_item_id: p
        for p in (
            await db.execute(
                select(UserWordProgress).where(
                    UserWordProgress.user_id == user.id,
                    UserWordProgress.lexicon_item_id.in_(item_ids),
                )
            )
        ).scalars()
    }
    hooks = await notes.notes_for(db, user.id, item_ids)
    out: list[ReviewItem] = []
    for t in tasks:
        item = t.item
        ev = first.get(t.id)
        prog = progress.get(item.id)
        recall = t.task_type == TaskType.RECALL
        # A chosen option is stored as its text; a revealed answer has nothing to show.
        answered = ev.answer if ev is not None and not ev.revealed else None
        out.append(
            ReviewItem(
                item_id=item.id,
                lemma=item.lemma,
                gender=item.gender,
                translation=item.translation_cs,
                task=t.task_type.value,
                first_try=t.first_try_correct,
                answered=answered,
                expected=item.lemma if recall else item.translation_cs,
                error=ev.error_tag if ev is not None and not ev.is_correct else None,
                passive_known=bool(prog and prog.passive_known),
                active_known=bool(prog and prog.active_known),
                next_review_at=prog.next_review_at if prog else None,
                note=hooks.get(item.id),
            )
        )
    return s.mode.value, out
