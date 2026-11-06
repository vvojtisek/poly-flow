"""German case lab: the declension paradigm plus nouns and adjectives to build phrases with.

Read-only reference material; nothing here is recorded as learning evidence.
"""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB, Auth
from app.domain import declension as d
from app.domain.enums import Language
from app.models import LexiconItem, UserWordProgress
from app.services.learning import _suitable

router = APIRouter(prefix="/api/v1/grammar/declension", tags=["grammar"])

MAX_NOUNS = 160
MAX_ADJECTIVES = 140


class Piece(BaseModel):
    stem: str
    ending: str


class CellOut(BaseModel):
    det: str
    case: str
    gender: str
    determiner: Piece | None
    adjective_ending: str
    kind: Literal["weak", "mixed", "strong"]
    signal: Literal["determiner", "adjective", "noun"]


class NounOut(BaseModel):
    lemma: str
    gender: str  # m, f, n, or pl for plural-only nouns
    translation: str
    met: bool  # the learner has had a lesson on it
    n_declension: bool
    singular: dict[str, Piece] | None
    plural: dict[str, Piece] | None


class AdjectiveOut(BaseModel):
    lemma: str
    stem: str | None  # None: indeclinable (lila, rosa)
    translation: str
    met: bool


class DeclensionOut(BaseModel):
    cells: list[CellOut]
    nouns: list[NounOut]
    adjectives: list[AdjectiveOut]


def _forms(lemma: str, gender: d.Gender, plural: str | None) -> dict[str, Piece]:
    out = {}
    for case in d.CASES:
        stem, ending = d.noun_form(lemma, gender, case, plural)
        out[case] = Piece(stem=stem, ending=ending)
    return out


def table() -> list[CellOut]:
    cells = []
    for det in d.DETS:
        for case in d.CASES:
            for gender in d.GENDERS:
                dt = d.determiner(det, case, gender)
                ending, kind = d.adjective_ending(det, case, gender)
                cells.append(
                    CellOut(
                        det=det,
                        case=case,
                        gender=gender,
                        determiner=Piece(stem=dt.stem, ending=dt.ending) if dt else None,
                        adjective_ending=ending,
                        kind=kind,
                        signal=d.signal_on(det, case, gender),
                    )
                )
    return cells


async def _words(db, user, pos: str, limit: int) -> list[tuple[LexiconItem, bool]]:
    p = UserWordProgress
    rows = await db.execute(
        select(LexiconItem, p.introduced_at)
        .outerjoin(p, (p.lexicon_item_id == LexiconItem.id) & (p.user_id == user.id))
        .where(LexiconItem.language == Language.DE, LexiconItem.pos == pos, _suitable(user))
        .order_by(p.introduced_at.is_(None), LexiconItem.frequency_rank)
        .limit(limit)
    )
    return [(item, introduced is not None) for item, introduced in rows.all()]


@router.get("", response_model=DeclensionOut)
async def declension(auth: Auth, db: DB) -> DeclensionOut:
    nouns = []
    for item, met in await _words(db, auth.acting, "NOUN", MAX_NOUNS):
        lemma = item.lemma
        if not d.declinable_noun(lemma):
            continue
        if lemma in d.PLURAL_ONLY:
            nouns.append(
                NounOut(
                    lemma=lemma, gender="pl", translation=item.translation_cs, met=met,
                    n_declension=False, singular=None, plural=_forms(lemma, "pl", lemma),
                )
            )  # fmt: skip
            continue
        gender = d.ARTICLE_GENDER.get(item.gender or "")
        if gender is None:
            continue
        plural = d.PLURALS.get(lemma)
        nouns.append(
            NounOut(
                lemma=lemma,
                gender=gender,
                translation=item.translation_cs,
                met=met,
                n_declension=d.is_n_declension(lemma),
                singular=_forms(lemma, gender, None),
                plural=_forms(lemma, "pl", plural) if plural else None,
            )
        )
    adjectives = [
        AdjectiveOut(
            lemma=item.lemma,
            stem=d.adjective_stem(item.lemma),
            translation=item.translation_cs,
            met=met,
        )
        for item, met in await _words(db, auth.acting, "ADJ", MAX_ADJECTIVES)
    ]
    return DeclensionOut(cells=table(), nouns=nouns, adjectives=adjectives)
