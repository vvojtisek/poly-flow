"""Tap-to-look-up: find the lexicon entry behind a word in a text the learner is reading.

Read-only. It matches the candidates from `app.domain.lookup` (and, for German, the present-tense
verb forms) against the lexicon the profile may see; the content filter applies as everywhere.
A word the profile has not met yet is still shown (a reading aid, like a story glossary), marked
as new; nothing is recorded, so looking up never counts as knowing.
"""

from dataclasses import dataclass

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.conjugation import conjugate
from app.domain.enums import Language
from app.domain.lookup import candidates
from app.models import LexiconItem, User, UserWordProgress
from app.services.learning import _suitable
from app.services.notes import notes_for
from app.services.words import _status

MAX_HITS = 3


@dataclass(frozen=True, slots=True)
class Hit:
    id: str
    lemma: str
    translation: str
    gender: str | None
    pos: str
    status: str | None  # None: not met yet; else the dictionary status
    note: str | None


async def _verb_lemmas(db: AsyncSession, user: User, word: str) -> list[str]:
    """German verbs whose present-tense form is this word (gibt → geben, stehe → aufstehen)."""
    rows = await db.scalars(
        select(LexiconItem.lemma).where(
            LexiconItem.language == "de", LexiconItem.pos.in_(("VERB", "AUX")), _suitable(user)
        )
    )
    out: list[str] = []
    for lemma in rows:
        try:
            forms = conjugate(lemma)
        except (IndexError, KeyError):
            continue
        if any(f.text == word for f in forms.values()):
            out.append(lemma.lower())
    return out


async def lookup(db: AsyncSession, user: User, language: Language, word: str) -> list[Hit]:
    cands = candidates(word, language)
    if not cands:
        return []
    if language == "de":
        # An exact present-tense form outranks suffix stripping (heiße → heißen before heiß).
        verbs = [v for v in await _verb_lemmas(db, user, cands[0]) if v != cands[0]]
        cands = [cands[0], *verbs, *(c for c in cands[1:] if c not in verbs)]
    li, p = LexiconItem, UserWordProgress
    order = {c: i for i, c in enumerate(cands)}
    rows = (
        await db.execute(
            select(li, _status().label("status"), p.id)
            .outerjoin(p, and_(p.lexicon_item_id == li.id, p.user_id == user.id))
            .where(li.language == language, func.lower(li.lemma).in_(cands), _suitable(user))
        )
    ).all()
    rows.sort(key=lambda r: (order[r[0].lemma.lower()], r[0].frequency_rank))
    rows = rows[:MAX_HITS]
    notes = await notes_for(db, user.id, [r[0].id for r in rows])
    return [
        Hit(
            id=str(item.id),
            lemma=item.lemma,
            translation=item.translation_cs,
            gender=item.gender,
            pos=item.pos,
            status=status if prog_id is not None else None,
            note=notes.get(item.id),
        )
        for item, status, prog_id in rows
    ]
