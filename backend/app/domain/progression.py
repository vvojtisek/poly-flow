"""Vocabulary progression: frequency-rank milestones and the voluntary extension beyond B2.

Curriculum: 100 -> 500 -> 1000 (A2) -> 2500 (B1) -> 4000 (B2 threshold) -> 5000 (full B2).
Beyond 5000 the app offers an open-ended, voluntary extension (6000+, passive-recognition
focus). It makes no CEFR claim there: progress past B2 depends on real use of the language
(conversation with people, media, culture), which the app can support but not replace.

The CEFR tags are heuristics. CEFR describes communicative ability, not vocabulary size; the
word counts only indicate a vocabulary consistent with that level.
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
    Milestone(500, "basic_500"),
    Milestone(1000, "a2", CefrLevel.A2),
    Milestone(2500, "b1", CefrLevel.B1),
    Milestone(4000, "b2_threshold", CefrLevel.B2),
    Milestone(5000, "b2_full", CefrLevel.B2),
    Milestone(6000, "extension_passive", voluntary=True, passive_focus=True),
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
