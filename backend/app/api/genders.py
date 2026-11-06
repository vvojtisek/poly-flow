"""Gender sorter: nouns with their gender and the ending rule behind it. Ungraded practice."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB, Auth
from app.domain import gender_hints as gh
from app.domain.enums import Language
from app.models import LexiconItem, UserWordProgress
from app.services.learning import _suitable

router = APIRouter(prefix="/api/v1/genders", tags=["learning"])

MAX_NOUNS = 300


class HintOut(BaseModel):
    suffix: str
    gender: str
    certainty: Literal["always", "usually"]
    exception: bool


class GenderNounOut(BaseModel):
    id: uuid.UUID
    lemma: str
    translation: str
    gender: str
    met: bool
    hint: HintOut | None


class RuleOut(BaseModel):
    suffix: str
    gender: str
    certainty: Literal["always", "usually"]


class GendersOut(BaseModel):
    language: Language
    genders: list[str]
    rules: list[RuleOut]
    nouns: list[GenderNounOut]


@router.get("", response_model=GendersOut)
async def genders(
    auth: Auth, db: DB, language: Annotated[Language | None, Query()] = None
) -> GendersOut:
    lang = language or auth.acting.active_language
    if lang not in gh.GENDERS:
        raise HTTPException(404, "no_grammatical_gender")
    p = UserWordProgress
    rows = (
        await db.execute(
            select(LexiconItem, p.introduced_at)
            .outerjoin(p, (p.lexicon_item_id == LexiconItem.id) & (p.user_id == auth.acting.id))
            .where(
                LexiconItem.language == lang,
                LexiconItem.pos == "NOUN",
                LexiconItem.gender.is_not(None),
                _suitable(auth.acting),
            )
            .order_by(p.introduced_at.is_(None), LexiconItem.frequency_rank)
            .limit(MAX_NOUNS)
        )
    ).all()
    nouns = []
    for item, introduced in rows:
        gender = gh.normalise(lang, item.gender)
        if gender is None:
            continue  # "m/f" nouns (l'enfant) have no single answer
        h = gh.hint(lang, item.lemma, gender)
        nouns.append(
            GenderNounOut(
                id=item.id,
                lemma=item.lemma,
                translation=item.translation_cs,
                gender=gender,
                met=introduced is not None,
                hint=HintOut(
                    suffix=h.suffix, gender=h.gender, certainty=h.certainty, exception=h.exception
                )
                if h
                else None,
            )
        )
    return GendersOut(
        language=lang,
        genders=list(gh.GENDERS[lang]),
        rules=[
            RuleOut(suffix=r.suffix, gender=r.gender, certainty=r.certainty)
            for r in gh.RULES.get(lang, ())
        ],
        nouns=nouns,
    )
