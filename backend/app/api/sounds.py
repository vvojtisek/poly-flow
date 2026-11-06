"""How letters sound: spelling-to-sound rules with example words from the lexicon. Reference."""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import and_, select

from app.api.deps import DB, Auth
from app.domain import sounds
from app.domain.enums import Language
from app.models import LexiconItem, UserWordProgress
from app.services.learning import _suitable

router = APIRouter(prefix="/api/v1/sounds", tags=["grammar"])

EXAMPLES = 4


class ExampleOut(BaseModel):
    id: str
    lemma: str
    translation: str
    start: int  # the highlighted letters, as indexes into lemma
    end: int
    met: bool


class RuleOut(BaseModel):
    id: str
    spelling: str
    czech: str
    note: str
    examples: list[ExampleOut]


@router.get("", response_model=list[RuleOut])
async def guide(
    auth: Auth, db: DB, language: Annotated[Language | None, Query()] = None
) -> list[RuleOut]:
    lang = language or auth.acting.active_language
    p, li = UserWordProgress, LexiconItem
    rows = (
        await db.execute(
            select(li.id, li.lemma, li.translation_cs, p.introduced_at)
            .outerjoin(p, and_(p.lexicon_item_id == li.id, p.user_id == auth.acting.id))
            .where(li.language == lang, _suitable(auth.acting))
            .order_by(li.frequency_rank)
        )
    ).all()
    # Words the learner has met come first, so they hear words they know; then by frequency.
    words = sorted(rows, key=lambda r: r.introduced_at is None)
    out: list[RuleOut] = []
    for rule in sounds.rules(lang):
        examples: list[ExampleOut] = []
        for r in words:
            if " " in r.lemma:
                continue
            span = rule.find(r.lemma.lower())
            if span is None:
                continue
            examples.append(
                ExampleOut(
                    id=str(r.id),
                    lemma=r.lemma,
                    translation=r.translation_cs,
                    start=span[0],
                    end=span[1],
                    met=r.introduced_at is not None,
                )
            )
            if len(examples) == EXAMPLES:
                break
        out.append(
            RuleOut(
                id=rule.id,
                spelling=rule.spelling,
                czech=rule.czech,
                note=rule.note,
                examples=examples,
            )
        )
    return out
