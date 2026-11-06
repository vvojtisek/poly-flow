"""Weekly recap (Týden v kostce): what one next step to suggest from a week's numbers. Pure.

The recap compares the last seven days with the seven before, without streaks or scores: a quiet
week is described, never punished. Accuracy is None when nothing was graded (unknown is not 0 %).
"""

from dataclasses import dataclass
from typing import Literal

Suggestion = Literal["check_due", "fix_mistakes", "new_lesson", "start_small", "keep_going"]


@dataclass(frozen=True, slots=True)
class Week:
    active_days: int
    graded: int
    correct: int
    practice: int
    introduced: int
    newly_known: int

    @property
    def accuracy(self) -> float | None:
        return self.correct / self.graded if self.graded else None


def trend(this: float | None, before: float | None, margin: float = 0.05) -> str | None:
    """ "up", "down" or "same" for accuracy; None when either week has no graded answers."""
    if this is None or before is None:
        return None
    if this > before + margin:
        return "up"
    if this < before - margin:
        return "down"
    return "same"


def suggest(week: Week, due_now: int, hard_words: int) -> Suggestion:
    """One next step, most useful first: reviews that are due, then this week's mistakes."""
    if due_now > 0:
        return "check_due"
    if week.active_days == 0:
        return "start_small"
    if hard_words > 0:
        return "fix_mistakes"
    if week.introduced < 5:
        return "new_lesson"
    return "keep_going"
