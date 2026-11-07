"""Dictation practice: hear an example sentence of a word you have met, type it, see the diff.

Ungraded: nothing here is knowledge evidence. The sentence text is only sent after an attempt.
"""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select, true

from app.api.deps import DB, Auth
from app.domain.dictation import compare, score
from app.domain.enums import Language
from app.models import LexiconItem, UserWordProgress
from app.services.learning import _suitable

router = APIRouter(prefix="/api/v1/dictation", tags=["learning"])


class NextOut(BaseModel):
    item_id: uuid.UUID | None
    words: int  # how many words the sentence has (a hint for the learner)
    pool: int  # sentences available for this profile


class SentenceOut(BaseModel):
    item_id: uuid.UUID
    sentence: str
    lemma: str
    translation: str


class CheckIn(BaseModel):
    item_id: uuid.UUID
    text: str = Field(max_length=600)


class MarkOut(BaseModel):
    expected: str | None
    typed: str | None
    verdict: str


class CheckOut(BaseModel):
    sentence: str
    lemma: str
    translation: str
    marks: list[MarkOut]
    score: float


def _pool(user, language: Language | None):
    """Example sentences of words this profile has had a lesson on (any language when None)."""
    p, li = UserWordProgress, LexiconItem
    return (
        select(li)
        .join(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
        .where(
            li.language == language if language else true(),
            _suitable(user),
            p.introduced_at.is_not(None),
            li.example_sentence.is_not(None),
            func.length(li.example_sentence) > 0,
        )
    )


@router.get("/next", response_model=NextOut)
async def next_sentence(
    auth: Auth,
    db: DB,
    language: Annotated[Language | None, Query()] = None,
    exclude: Annotated[list[uuid.UUID] | None, Query(max_length=50)] = None,
) -> NextOut:
    lang = language or auth.acting.active_language
    q = _pool(auth.acting, lang)
    pool = await db.scalar(select(func.count()).select_from(q.subquery())) or 0
    if exclude:
        q = q.where(LexiconItem.id.not_in(exclude))
    item = (await db.execute(q.order_by(func.random()).limit(1))).scalar_one_or_none()
    if item is None:
        return NextOut(item_id=None, words=0, pool=pool)
    return NextOut(item_id=item.id, words=len((item.example_sentence or "").split()), pool=pool)


@router.post("/check", response_model=CheckOut)
async def check(body: CheckIn, auth: Auth, db: DB) -> CheckOut:
    item = (
        await db.execute(_pool(auth.acting, None).where(LexiconItem.id == body.item_id))
    ).scalar_one_or_none()
    if item is None or not item.example_sentence:
        raise HTTPException(404, "sentence_not_found")
    marks = compare(item.example_sentence, body.text)
    return CheckOut(
        sentence=item.example_sentence,
        lemma=item.lemma,
        translation=item.translation_cs,
        marks=[MarkOut(expected=m.expected, typed=m.typed, verdict=m.verdict) for m in marks],
        score=round(score(marks), 3),
    )


@router.get("/sentences", response_model=list[SentenceOut])
async def sentences(
    auth: Auth,
    db: DB,
    language: Annotated[Language | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=40)] = 20,
    order: Annotated[Literal["random", "recent"], Query()] = "random",
) -> list[SentenceOut]:
    """Sentences shown with their text, for shadowing (listen, repeat, compare). Ungraded.

    ``recent`` lists the most recently introduced words first (the latest lesson's words, while
    they are fresh); ``random`` samples the whole taught pool.
    """
    lang = language or auth.acting.active_language
    q = _pool(auth.acting, lang)
    if order == "recent":
        q = q.order_by(
            UserWordProgress.introduced_at.desc(), LexiconItem.frequency_rank, LexiconItem.id
        )
    else:
        q = q.order_by(func.random())
    items = (await db.execute(q.limit(limit))).scalars().all()
    return [
        SentenceOut(
            item_id=i.id,
            sentence=i.example_sentence or "",
            lemma=i.lemma,
            translation=i.translation_cs,
        )
        for i in items
    ]
