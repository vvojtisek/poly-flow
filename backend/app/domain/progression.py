"""Vocabulary progression: frequency-rank milestones and the voluntary extension beyond B2.

Curriculum: 100 -> 500 (A1) -> 1000 (A2) -> 2500 (B1) -> 4000 (B2 threshold) -> 5000 (full B2).
Beyond 5000 the app offers a voluntary, passive-focused extension. At 8000 it labels the
app-specific C1 vocabulary band (product decision 2026-11-07). This is not CEFR certification:
communicative proficiency still depends on real use of the language.

The CEFR tags are heuristics. CEFR describes communicative ability, not vocabulary size; the
word counts only indicate a vocabulary consistent with that level. The level exams
(`app.domain.level_exam`) take their bands from these tags.
"""

from dataclasses import dataclass

from app.domain.enums import CefrLevel

EXTENSION_STEP = 1000


@dataclass(frozen=True, slots=True)
class Milestone:
    rank: int
    key: str  # stable id; UI copy is localised in the frontend
    cefr: CefrLevel | None = None
    voluntary: bool = False  # True = beyond the curriculum, never required or nagged about
    passive_focus: bool = False  # True = drills prioritise recognition over production


MILESTONES: tuple[Milestone, ...] = (
    Milestone(100, "core_100"),
    Milestone(500, "basic_500", CefrLevel.A1),
    Milestone(1000, "a2", CefrLevel.A2),
    Milestone(2500, "b1", CefrLevel.B1),
    Milestone(4000, "b2_threshold", CefrLevel.B2),
    Milestone(5000, "b2_full", CefrLevel.B2),
    Milestone(6000, "extension_passive", voluntary=True, passive_focus=True),
    Milestone(7000, "extension_passive", voluntary=True, passive_focus=True),
    Milestone(8000, "c1_vocabulary", CefrLevel.C1, voluntary=True, passive_focus=True),
)

CURRICULUM_END = 5000  # last required milestone (full B2)


def is_extension(rank: int) -> bool:
    """Ranks past the curriculum: voluntary, passive-focused, no CEFR claim."""
    return rank > CURRICULUM_END


def frequency_band(rank: int) -> int:
    """Smallest milestone >= rank; past the last milestone, the next multiple of EXTENSION_STEP."""
    if rank < 1:
        raise ValueError(f"rank must be >= 1, got {rank}")
    for m in MILESTONES:
        if rank <= m.rank:
            return m.rank
    return -(-rank // EXTENSION_STEP) * EXTENSION_STEP


# Vocabulary levels for grouping words: the indicative CEFR tag of the first labelled milestone at
# or above a rank (A1 includes the core 100; 5001-8000 is the app-specific C1 vocabulary band).
# Past the last labelled milestone a rank has no level: the voluntary extension, keyed below.
EXTENSION_LEVEL = "extension"


def vocabulary_level(rank: int) -> str:
    """Indicative level key of a frequency rank: a CEFR value, or EXTENSION_LEVEL past 8000."""
    if rank < 1:
        raise ValueError(f"rank must be >= 1, got {rank}")
    for m in MILESTONES:
        if rank <= m.rank and m.cefr is not None:
            return m.cefr.value
    return EXTENSION_LEVEL


def vocabulary_levels() -> list[tuple[str, int, int | None]]:
    """(level key, first rank, last rank or None for open-ended), in curriculum order."""
    out: list[tuple[str, int, int | None]] = []
    lo = 1
    for m in MILESTONES:
        if m.cefr is None:
            continue
        if out and out[-1][0] == m.cefr.value:
            out[-1] = (m.cefr.value, out[-1][1], m.rank)
        else:
            out.append((m.cefr.value, lo, m.rank))
        lo = m.rank + 1
    out.append((EXTENSION_LEVEL, lo, None))
    return out
