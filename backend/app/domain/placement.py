"""Adaptive placement test (rozřazovací test). Pure functions; no I/O.

The test estimates `level`: the frequency rank up to which a learner recognises words. It keeps
a posterior over the level on a log-rank grid, asks the word nearest its median and stops once
the credible interval is narrow enough. Only the lexicon ranks that exist are testable: the
`ceiling` is the highest available rank, and a level at the ceiling means "at least that".

The response model and its constants are pilot assumptions, not a calibrated item-response
model: a learner recognises words well below their level, rarely above it, and sometimes
guesses or slips. Changing a constant means a new `version`.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlacementPolicy:
    version: str = "p1"
    # Grid over ln(level) from ln(floor) (knows nothing) to ln(ceiling * headroom).
    grid_points: int = 241
    floor: float = 0.5
    headroom: float = 2.0
    # P(correct | rank, level) = guess + (1 - guess - lapse) * sigmoid(slope * ln(level / rank))
    # A "Nevím" button lowers guessing below the 1-in-4 of the recognition options.
    guess: float = 0.15
    lapse: float = 0.05
    slope: float = 3.0
    # Stop rules: at least `min_items`, at most `max_items`; stop earlier once the central
    # `credible` interval spans at most `stop_ratio` (high / low rank) or `stop_span` ranks
    # (near the start of the list a ratio means only a word or two).
    min_items: int = 8
    max_items: int = 25
    credible: float = 0.8
    stop_ratio: float = 2.0
    stop_span: int = 5


PLACEMENT = PlacementPolicy()


@dataclass(frozen=True, slots=True)
class Estimate:
    level: int  # recognised up to about this rank (0 = none of the tested words)
    low: int  # credible interval, clipped to [0, ceiling]
    high: int
    at_ceiling: bool  # recognises (nearly) every available word: the true level may be higher


def _grid(ceiling: int, policy: PlacementPolicy) -> list[float]:
    lo, hi = math.log(policy.floor), math.log(max(ceiling, 1) * policy.headroom)
    step = (hi - lo) / (policy.grid_points - 1)
    return [lo + i * step for i in range(policy.grid_points)]


def p_correct(rank: int, log_level: float, policy: PlacementPolicy = PLACEMENT) -> float:
    z = policy.slope * (log_level - math.log(rank))
    return policy.guess + (1 - policy.guess - policy.lapse) / (1 + math.exp(-z))


def _posterior(
    answers: list[tuple[int, bool]], ceiling: int, policy: PlacementPolicy
) -> tuple[list[float], list[float]]:
    grid = _grid(ceiling, policy)
    logw = [0.0] * len(grid)  # uniform prior on ln(level)
    for rank, correct in answers:
        for i, x in enumerate(grid):
            p = p_correct(rank, x, policy)
            logw[i] += math.log(p if correct else 1 - p)
    top = max(logw)
    w = [math.exp(v - top) for v in logw]
    total = sum(w)
    return grid, [v / total for v in w]


def _quantile(grid: list[float], w: list[float], q: float) -> float:
    acc = 0.0
    for x, p in zip(grid, w, strict=True):
        acc += p
        if acc >= q:
            return math.exp(x)
    return math.exp(grid[-1])


def _summary(
    answers: list[tuple[int, bool]], ceiling: int, policy: PlacementPolicy
) -> tuple[float, float, float]:
    grid, w = _posterior(answers, ceiling, policy)
    tail = (1 - policy.credible) / 2
    return _quantile(grid, w, tail), _quantile(grid, w, 0.5), _quantile(grid, w, 1 - tail)


def is_finished(
    answers: list[tuple[int, bool]], ceiling: int, policy: PlacementPolicy = PLACEMENT
) -> bool:
    if len(answers) >= policy.max_items:
        return True
    if len(answers) < policy.min_items:
        return False
    low, _, high = _summary(answers, ceiling, policy)
    if low >= ceiling:  # recognises everything there is to ask
        return True
    return high / max(low, policy.floor) <= policy.stop_ratio or high - low <= policy.stop_span


def next_rank(
    answers: list[tuple[int, bool]], ceiling: int, policy: PlacementPolicy = PLACEMENT
) -> int | None:
    """Rank to ask next (the posterior median, within the lexicon), or None to stop."""
    if ceiling < 1 or is_finished(answers, ceiling, policy):
        return None
    _, median, _ = _summary(answers, ceiling, policy)
    return min(max(round(median), 1), ceiling)


def estimate(
    answers: list[tuple[int, bool]], ceiling: int, policy: PlacementPolicy = PLACEMENT
) -> Estimate | None:
    """The placement result, or None when too few answers support one."""
    if ceiling < 1 or len(answers) < policy.min_items:
        return None
    low, median, high = _summary(answers, ceiling, policy)

    def clip(v: float) -> int:
        return min(max(math.floor(v), 0), ceiling)

    return Estimate(level=clip(median), low=clip(low), high=clip(high), at_ceiling=low >= ceiling)
