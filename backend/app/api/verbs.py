"""German verb lab: present tense forms of the lexicon's verbs, built by rules. Reference only."""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB, Auth
from app.domain import conjugation as cj
from app.domain.enums import Language
from app.models import LexiconItem, UserWordProgress
from app.services.learning import _suitable

router = APIRouter(prefix="/api/v1/grammar/verbs", tags=["grammar"])

MAX_VERBS = 400


class FormOut(BaseModel):
    stem: str
    ending: str
    changed: bool


class VerbOut(BaseModel):
    lemma: str
    translation: str
    met: bool
    prefix: str | None
    features: list[str]
    forms: dict[str, FormOut]  # ich, du, er, wir, ihr, sie


@router.get("", response_model=list[VerbOut])
async def verbs(auth: Auth, db: DB) -> list[VerbOut]:
    p = UserWordProgress
    rows = (
        await db.execute(
            select(LexiconItem, p.introduced_at)
            .outerjoin(p, (p.lexicon_item_id == LexiconItem.id) & (p.user_id == auth.acting.id))
            .where(
                LexiconItem.language == Language.DE,
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
            continue  # multi-word entries ("Rad fahren") are left out
        forms = cj.conjugate(lemma)
        out.append(
            VerbOut(
                lemma=lemma,
                translation=item.translation_cs,
                met=introduced is not None,
                prefix=forms["du"].prefix,
                features=list(cj.features(lemma)),
                forms={
                    k: FormOut(stem=f.stem, ending=f.ending, changed=f.changed)
                    for k, f in forms.items()
                },
            )
        )
    return out
