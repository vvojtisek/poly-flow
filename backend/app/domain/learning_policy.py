"""Versioned learning policy (plan §4). Pure functions; no I/O.

Thresholds are pilot values. Changing any of them means a new POLICY version so stored
progress can be traced to the rules that produced it.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class LearningPolicy:
    # v2: only checks (Ověření) count as evidence; lessons introduce words in context and their
    # practice is never graded toward knowledge. Words become checkable the next local day.
    # v3: a recall task can be answered by voice. A transcript that is exactly the word, with
    # every matched word at least `spoken_min_confidence`, counts like a correct written answer
    # (active evidence, no orthography measurement). Anything else is "not understood" and
    # changes nothing: speech recognition errors are not evidence of not knowing a word.
    # v4: wrong answers carry an error tag (meaning, gender, spelling, ...), a recall answer
    # with the wrong German article is still correct but tagged `gender`, and a lesson opens
    # with up to `remediation_per_lesson` words the profile missed in a recent check
    # (ungraded practice, like the rest of the lesson).
    version: str = "v4"
    # passive_known: correct recognition (or production) in a check, without a hint
    passive_required_correct: int = 3
    passive_required_days: int = 2
    # active_known: correct written production in a check, without a hint
    active_required_correct: int = 3
    active_required_days: int = 2
    # MASTERED: both known, then a successful check at least this long afterwards
    mastery_delay: timedelta = timedelta(days=7)
    # Spacing after consecutive first-try successes; the last value repeats.
    review_intervals: tuple[timedelta, ...] = tuple(timedelta(days=d) for d in (1, 2, 4, 7, 14, 30))
    # No verified error-free use for this long -> back to priority review (plan §4)
    decay_after: timedelta = timedelta(days=30)
    # Effective retention past the decay window halves every this many days.
    retention_half_life: timedelta = timedelta(days=30)
    # Session composition: a check holds at most this many words...
    session_max_tasks: int = 12
    # ...and a lesson introduces at most this many (each practised twice).
    new_items_per_session: int = 4
    # Recently missed words practised at the start of the next lesson, and the window that
    # counts as "recently" (also used by the weak-spot overview).
    remediation_per_lesson: int = 2
    remediation_window: timedelta = timedelta(days=21)
    # Lowest Whisper word probability for a spoken match. Provisional: transcript confidence
    # of real learner recordings is stored per event so this can be set from data.
    spoken_min_confidence: float = 0.5
    # Exponential smoothing weight of the latest orthography measurement
    orthography_weight: float = 0.3


POLICY = LearningPolicy()


def next_review_interval(streak: int, policy: LearningPolicy = POLICY) -> timedelta:
    """Interval after `streak` consecutive first-try successes (streak >= 1)."""
    idx = min(max(streak, 1), len(policy.review_intervals)) - 1
    return policy.review_intervals[idx]


def effective_retention(
    last_error_free_at: datetime | None, now: datetime, policy: LearningPolicy = POLICY
) -> float | None:
    """Derived on read from the last verified success; never written back.

    Recomputing from the same base keeps repeated decay sweeps from compounding.
    """
    if last_error_free_at is None:
        return None
    overdue = (now - last_error_free_at) - policy.decay_after
    if overdue <= timedelta(0):
        return 1.0
    return math.pow(0.5, overdue / policy.retention_half_life)


def smooth(old: float | None, new: float, policy: LearningPolicy = POLICY) -> float:
    if old is None:
        return new
    return round(old * (1 - policy.orthography_weight) + new * policy.orthography_weight, 4)


@dataclass(frozen=True, slots=True)
class GrammarPolicy:
    """Grammar units (plan P5): same learn/check split and spacing as words.

    g1: a unit is "known" after `known_required_correct` first-try correct check answers on at
    least `known_required_days` days; MASTERED after a successful check `mastery_delay` later.
    A missed check answer makes the unit due the next local day and brings that exercise back.
    """

    version: str = "g1"
    known_required_correct: int = 3
    known_required_days: int = 2
    mastery_delay: timedelta = timedelta(days=7)
    review_intervals: tuple[timedelta, ...] = tuple(timedelta(days=d) for d in (1, 2, 4, 7, 14, 30))
    decay_after: timedelta = timedelta(days=30)
    # A grammar check covers at most this many due units, this many exercises each.
    check_max_units: int = 4
    check_exercises_per_unit: int = 2
    # A grammar lesson adds up to this many exercises missed recently in other units.
    lesson_remediation: int = 2
    # "Recently" for remediation and weak spots.
    remediation_window: timedelta = timedelta(days=21)


GRAMMAR_POLICY = GrammarPolicy()
