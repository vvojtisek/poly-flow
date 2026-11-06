"""CEFR placement diagnostic (rozřazovací test, part 2): A1 to B2+. Pure functions; no I/O.

Part 1 of the placement test (`app.domain.placement`) measures vocabulary size by frequency
rank. This part estimates a CEFR band from grammar, vocabulary in context, reading, listening
and idioms, using an item bank per language (`backend/data/diagnostic/<lang>.diagnostic.json`).

Model: a three-parameter logistic item response model on one ability scale `theta`,

    P(correct | theta, item) = guess + (1 - guess - lapse) * sigmoid(slope * (theta - b))

where `b` is the item's band difficulty (A1 -2, A2 -1, B1 0, B2 1, B2+ 2). The test keeps a
posterior over theta on a grid, asks the item with the most Fisher information at the posterior
mean (rotating skills, so one skill cannot dominate) and stops when the posterior is narrow
enough. A learner who answers A1/A2 items well climbs into B1 and B2 within a few items; one
who struggles is held around the band where the answers turn.

These constants are pilot assumptions, not a calibration on learner data: item difficulties are
the nominal band of the item. CEFR describes communicative ability; a 20-item test of
recognition-style items indicates a band, it does not certify one. "B2+" means "above the B2
items here", not C1. Changing a constant means a new `version`.
"""

import math
import random
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.enums import CefrLevel, ContentFlag, Language

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SLUG = r"^[a-z0-9][a-z0-9-]{0,63}$"


class Skill(StrEnum):
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    READING = "reading"
    LISTENING = "listening"
    IDIOM = "idiom"


# Item bands, easiest first. C1 is the above-B2 probe: reported as "B2+", never as C1.
BANDS: tuple[CefrLevel, ...] = (
    CefrLevel.A1,
    CefrLevel.A2,
    CefrLevel.B1,
    CefrLevel.B2,
    CefrLevel.C1,
)
DIFFICULTY: dict[CefrLevel, float] = {b: float(i - 2) for i, b in enumerate(BANDS)}
MIN_ITEMS_PER_BAND = 6


def band_label(level: CefrLevel | None) -> str:
    if level is None:
        return "pre-A1"
    return "B2+" if level == CefrLevel.C1 else level.value


# ---------------------------------------------------------------- item bank schema


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Annotated[str, StringConstraints(pattern=SLUG)]
    level: CefrLevel
    skill: Skill
    prompt: NonEmpty  # a sentence with one "___", or a question (Czech for reading/listening)
    context: str | None = None  # reading: the passage, in the target language
    audio: str | None = None  # listening: the text spoken by TTS, never shown before answering
    options: list[NonEmpty] = Field(min_length=3, max_length=5)
    answer: NonEmpty
    explain: NonEmpty  # Czech: why the answer is right
    content_flags: list[ContentFlag] = Field(default_factory=list)

    @model_validator(mode="after")
    def _shape(self) -> "Item":
        if self.level not in BANDS:
            raise ValueError(f"{self.id}: level must be one of {[b.value for b in BANDS]}")
        if len(set(self.options)) != len(self.options):
            raise ValueError(f"{self.id}: duplicate options")
        if self.answer not in self.options:
            raise ValueError(f"{self.id}: the answer must be one of the options")
        if self.skill == Skill.READING and not (self.context and self.context.strip()):
            raise ValueError(f"{self.id}: a reading item needs a context passage")
        if self.skill == Skill.LISTENING and not (self.audio and self.audio.strip()):
            raise ValueError(f"{self.id}: a listening item needs audio text")
        if self.skill != Skill.LISTENING and self.audio is not None:
            raise ValueError(f"{self.id}: only listening items carry audio")
        return self

    @property
    def difficulty(self) -> float:
        return DIFFICULTY[self.level]


class ItemBank(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Language
    source: NonEmpty
    license: NonEmpty
    revision: NonEmpty
    review_status: Literal["unreviewed", "reviewed"]
    note: str = ""
    items: list[Item]

    @model_validator(mode="after")
    def _coverage(self) -> "ItemBank":
        ids = Counter(i.id for i in self.items)
        dupes = [k for k, n in ids.items() if n > 1]
        if dupes:
            raise ValueError(f"duplicate item ids: {dupes}")
        per_band = Counter(i.level for i in self.items)
        thin = [b.value for b in BANDS if per_band[b] < MIN_ITEMS_PER_BAND]
        if thin:
            raise ValueError(f"bands with fewer than {MIN_ITEMS_PER_BAND} items: {thin}")
        return self

    def by_id(self) -> dict[str, Item]:
        return {i.id: i for i in self.items}


# ---------------------------------------------------------------- adaptive model


@dataclass(frozen=True, slots=True)
class DiagnosticPolicy:
    version: str = "d1"
    grid_lo: float = -4.0
    grid_hi: float = 4.0
    grid_points: int = 161
    prior_sd: float = 1.6
    default_prior_mean: float = -1.0  # A2: the test opens in the middle of the lower bands
    # Four options plus "Nevím": an honest learner rarely guesses.
    guess: float = 0.15
    lapse: float = 0.05
    slope: float = 1.7
    min_items: int = 10
    max_items: int = 22
    stop_sd: float = 0.42
    # A band counts as reached when the learner gets its items right well above chance:
    # sigmoid(slope * offset) = 0.65 at theta = band difficulty + offset.
    reach_offset: float = 0.36


DIAGNOSTIC = DiagnosticPolicy()


def p_correct(theta: float, b: float, policy: DiagnosticPolicy = DIAGNOSTIC) -> float:
    return policy.guess + (1 - policy.guess - policy.lapse) / (
        1 + math.exp(-policy.slope * (theta - b))
    )


def information(theta: float, b: float, policy: DiagnosticPolicy = DIAGNOSTIC) -> float:
    """Fisher information of a 3PL item at theta."""
    p = p_correct(theta, b, policy)
    lo, hi = policy.guess, 1 - policy.lapse
    if p <= lo or p >= hi:
        return 0.0
    dp = policy.slope * (p - lo) * (hi - p) / (hi - lo)
    return dp * dp / (p * (1 - p))


def prior_mean_from_vocabulary(rank_level: int | None) -> float:
    """Start from the vocabulary part's result when there is one (rank 100 ~ A1, 1000 ~ A2)."""
    if rank_level is None or rank_level < 1:
        return DIAGNOSTIC.default_prior_mean
    x = -2.0 + 1.2 * math.log10(max(rank_level, 10) / 100)
    return max(-2.5, min(1.0, x))


@dataclass(frozen=True, slots=True)
class Posterior:
    mean: float
    sd: float
    low: float  # 10th percentile
    high: float  # 90th percentile


def posterior(
    answers: list[tuple[float, bool | None]],
    prior_mean: float,
    policy: DiagnosticPolicy = DIAGNOSTIC,
) -> Posterior:
    """`answers`: (item difficulty, correct). None ("Nevím") counts as a wrong answer."""
    n = policy.grid_points
    step = (policy.grid_hi - policy.grid_lo) / (n - 1)
    grid = [policy.grid_lo + i * step for i in range(n)]
    logw = [-0.5 * ((x - prior_mean) / policy.prior_sd) ** 2 for x in grid]
    for b, correct in answers:
        for i, x in enumerate(grid):
            p = p_correct(x, b, policy)
            logw[i] += math.log(p if correct else 1 - p)
    top = max(logw)
    w = [math.exp(v - top) for v in logw]
    total = sum(w)
    w = [v / total for v in w]
    mean = sum(x * p for x, p in zip(grid, w, strict=True))
    var = sum((x - mean) ** 2 * p for x, p in zip(grid, w, strict=True))

    def quantile(q: float) -> float:
        acc = 0.0
        for x, p in zip(grid, w, strict=True):
            acc += p
            if acc >= q:
                return x
        return grid[-1]

    return Posterior(mean=mean, sd=math.sqrt(var), low=quantile(0.1), high=quantile(0.9))


def is_finished(
    post: Posterior, asked: int, available: int, policy: DiagnosticPolicy = DIAGNOSTIC
) -> bool:
    if asked >= policy.max_items or available == 0:
        return True
    return asked >= policy.min_items and post.sd <= policy.stop_sd


def choose_item(
    candidates: list[Item],
    asked_skills: list[Skill],
    theta: float,
    rng: random.Random,
    policy: DiagnosticPolicy = DIAGNOSTIC,
) -> Item | None:
    """The most informative item at theta; among near-equal ones, the least asked skill."""
    if not candidates:
        return None
    asked = Counter(asked_skills)
    best = max(information(theta, c.difficulty, policy) for c in candidates)
    # Items within 85 % of the best information are interchangeable; rotate skills among them.
    near = [c for c in candidates if information(theta, c.difficulty, policy) >= 0.85 * best]
    fewest = min(asked[c.skill] for c in near)
    pool = [c for c in near if asked[c.skill] == fewest]
    return rng.choice(pool)


def reached_band(theta: float, policy: DiagnosticPolicy = DIAGNOSTIC) -> CefrLevel | None:
    """Highest band whose items the learner gets right well above chance at `theta`."""
    reached = None
    for b in BANDS:
        if theta >= DIFFICULTY[b] + policy.reach_offset:
            reached = b
    return reached


def next_band(level: CefrLevel | None) -> CefrLevel | None:
    if level is None:
        return BANDS[0]
    i = BANDS.index(level)
    return BANDS[i + 1] if i + 1 < len(BANDS) else None


@dataclass(slots=True)
class SkillReport:
    skill: Skill
    asked: int = 0
    correct: int = 0
    expected: float = 0.0  # correct answers the overall estimate predicts

    @property
    def verdict(self) -> str:
        """Above / below / as the overall level predicts; 'few' when too little was asked."""
        if self.asked < 2:
            return "few"
        diff = self.correct - self.expected
        if diff >= 1.0:
            return "strong"
        if diff <= -1.0:
            return "weak"
        return "even"


@dataclass(slots=True)
class Result:
    level: CefrLevel | None  # None = below A1 items (beginner)
    theta: float
    sd: float
    low_level: CefrLevel | None
    high_level: CefrLevel | None
    asked: int
    correct: int
    skills: list[SkillReport] = field(default_factory=list)
    bands: dict[str, tuple[int, int]] = field(default_factory=dict)  # band -> (correct, asked)


def result(
    answered: list[tuple[Item, bool | None]],
    prior_mean: float,
    policy: DiagnosticPolicy = DIAGNOSTIC,
) -> Result:
    post = posterior([(i.difficulty, c) for i, c in answered], prior_mean, policy)
    reports = {s: SkillReport(s) for s in Skill}
    bands: dict[str, list[int]] = {}
    for item, correct in answered:
        r = reports[item.skill]
        r.asked += 1
        r.correct += int(bool(correct))
        r.expected += p_correct(post.mean, item.difficulty, policy)
        acc = bands.setdefault(band_label(item.level), [0, 0])
        acc[0] += int(bool(correct))
        acc[1] += 1
    return Result(
        level=reached_band(post.mean, policy),
        theta=post.mean,
        sd=post.sd,
        low_level=reached_band(post.low, policy),
        high_level=reached_band(post.high, policy),
        asked=len(answered),
        correct=sum(1 for _, c in answered if c),
        skills=[r for r in reports.values() if r.asked],
        bands={k: (v[0], v[1]) for k, v in bands.items()},
    )


def band_at_most(unit_level: CefrLevel, placed: CefrLevel | None) -> bool:
    """A curriculum node of `unit_level` lies at or below the placed band."""
    if placed is None:
        return False
    return BANDS.index(unit_level) <= BANDS.index(placed)
