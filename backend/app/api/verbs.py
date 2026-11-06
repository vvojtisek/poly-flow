"""Verb lab: present tense forms of the lexicon's verbs, built by rules. Reference only.

German uses `app.domain.conjugation`, French and Italian `app.domain.conjugation_romance`.
English is left out: its present tense has one change (he/she -s) and needs no table.
"""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB, Auth
from app.domain import conjugation as cj
from app.domain import conjugation_romance as rj
from app.models import LexiconItem, UserWordProgress
from app.services.learning import _suitable

router = APIRouter(prefix="/api/v1/grammar/verbs", tags=["grammar"])

MAX_VERBS = 400
DE_PRONOUNS = ("ich", "du", "er/sie/es", "wir", "ihr", "sie/Sie")
VerbLanguage = Literal["de", "fr", "it"]


class FormOut(BaseModel):
    pronoun: str
    stem: str
    ending: str
    changed: bool


class VerbOut(BaseModel):
    lemma: str
    translation: str
    met: bool
    prefix: str | None  # German separable prefix, said at the end of the clause
    features: list[str]
    forms: list[FormOut]  # six persons: 1st-3rd singular, then 1st-3rd plural


def _build(lemma: str, language: VerbLanguage) -> tuple[list[FormOut], str | None, list[str]]:
    if language == "de":
        de = cj.conjugate(lemma)
        forms = [
            FormOut(pronoun=pr, stem=f.stem, ending=f.ending, changed=f.changed)
            for pr, f in zip(DE_PRONOUNS, de.values(), strict=True)
        ]
        return forms, de["du"].prefix, list(cj.features(lemma))
    rforms = rj.conjugate_fr(lemma) if language == "fr" else rj.conjugate_it(lemma)
    forms = [
        FormOut(pronoun=f.pronoun, stem=f.stem, ending=f.ending, changed=f.changed) for f in rforms
    ]
    return forms, None, list(rj.features(lemma, language))


@router.get("", response_model=list[VerbOut])
async def verbs(auth: Auth, db: DB, language: VerbLanguage = "de") -> list[VerbOut]:
    p = UserWordProgress
    rows = (
        await db.execute(
            select(LexiconItem, p.introduced_at)
            .outerjoin(p, (p.lexicon_item_id == LexiconItem.id) & (p.user_id == auth.acting.id))
            .where(
                LexiconItem.language == language,
                LexiconItem.pos.in_(("VERB", "AUX")),
                _suitable(auth.acting),
            )
            .order_by(p.introduced_at.is_(None), LexiconItem.frequency_rank)
            .limit(MAX_VERBS)
        )
    ).all()
    out = []
    for item, introduced in rows:
        lemma = item.lemma.split("/")[0].strip()
        if not lemma.isalpha():
            continue  # multi-word or reflexive entries ("Rad fahren", "s'appeler") are left out
        try:
            forms, prefix, feats = _build(lemma, language)
        except ValueError:
            continue  # not an infinitive the rules know (a data error); skip, don't fail the lab
        out.append(
            VerbOut(
                lemma=lemma,
                translation=item.translation_cs,
                met=introduced is not None,
                prefix=prefix,
                features=feats,
                forms=forms,
            )
        )
    return out
