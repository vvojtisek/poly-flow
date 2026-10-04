"""Vocabulary level exams (A1, A2, B1, B2). Pure rules; no I/O.

An exam asks a fresh random sample of words from one level's frequency band, once each, as
recognition with "Nevím" (like Ověření: one attempt, no hints, no timer). Passing earns a
vocabulary level badge. It is a vocabulary check, not a CEFR certificate: CEFR describes
communicative ability, which word recognition alone does not establish.

Bands come from the CEFR tags in `app.domain.progression`: each level covers the ranks above
the previous level up to its highest milestone (A1 1-500, A2 501-1000, B1 1001-2500,
B2 2501-5000). Levels are taken in order: a band builds on the ones below it.

Pass mark: 26 of 30, the mastery criterion of the Vocabulary Levels Test (Schmitt, Schmitt and
Clapham 2001). With honest "Nevím" answers a learner who knows 90 % of the band passes about
4 times in 5, one who knows 80 % about 1 in 4, one who knows 70 % about 1 in 30. These figures
follow from the binomial model, not from data; changing a constant means a new `version`.
"""

import math
from dataclasses import dataclass

from app.domain.enums import CefrLevel
from app.domain.progression import MILESTONES


@dataclass(frozen=True, slots=True)
class ExamPolicy:
    version: str = "e1"
    questions: int = 30
    pass_correct: int = 26
    # The exam opens when this share of the band's words is known passively (recognised in
    # Ověření on several days), or a placement test placed the learner past the band.
    ready_share: float = 0.8
    # The band counts as imported when the lexicon holds this share of its ranks (imports may
    # leave gaps, e.g. dropped duplicates). Below it a sample would not represent the level.
    complete_share: float = 0.9


EXAM = ExamPolicy()


@dataclass(frozen=True, slots=True)
class ExamLevel:
    level: CefrLevel
    low: int  # ranks above this...
    high: int  # ...up to and including this

    @property
    def size(self) -> int:
        return self.high - self.low


def _levels() -> tuple[ExamLevel, ...]:
    out: list[ExamLevel] = []
    low = 0
    for level in (CefrLevel.A1, CefrLevel.A2, CefrLevel.B1, CefrLevel.B2):
        high = max(m.rank for m in MILESTONES if m.cefr is level)
        out.append(ExamLevel(level, low, high))
        low = high
    return tuple(out)


LEVELS: tuple[ExamLevel, ...] = _levels()
BY_LEVEL: dict[CefrLevel, ExamLevel] = {e.level: e for e in LEVELS}


def previous(level: CefrLevel) -> CefrLevel | None:
    i = [e.level for e in LEVELS].index(level)
    return LEVELS[i - 1].level if i else None


def band_complete(exam: ExamLevel, lexicon_items: int, policy: ExamPolicy = EXAM) -> bool:
    return lexicon_items >= math.ceil(exam.size * policy.complete_share)


def ready(
    exam: ExamLevel,
    pool: int,
    known: int,
    placement_level: int | None,
    policy: ExamPolicy = EXAM,
) -> bool:
    """Enough of the band is known (or a placement test reached past it) to try the exam."""
    if placement_level is not None and placement_level >= exam.high:
        return True
    return pool > 0 and known >= math.ceil(pool * policy.ready_share)


def passed(correct: int, answered: int, policy: ExamPolicy = EXAM) -> bool:
    """Every question answered and at least the pass mark right on the first try."""
    return answered >= policy.questions and correct >= policy.pass_correct
