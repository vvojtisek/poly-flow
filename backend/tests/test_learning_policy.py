from datetime import UTC, datetime, timedelta

from app.domain.learning_policy import POLICY, effective_retention, next_review_interval, smooth

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def test_review_intervals_grow_then_cap():
    days = [next_review_interval(s).days for s in range(1, 9)]
    assert days == [1, 2, 4, 7, 14, 30, 30, 30]


def test_effective_retention_is_derived_not_compounded():
    assert effective_retention(None, T0) is None
    assert effective_retention(T0, T0 + timedelta(days=30)) == 1.0
    assert effective_retention(T0, T0 + POLICY.decay_after + POLICY.retention_half_life) == 0.5
    # Same inputs, same output: repeated evaluation cannot keep lowering it.
    later = T0 + timedelta(days=75)
    assert effective_retention(T0, later) == effective_retention(T0, later)


def test_smoothing():
    assert smooth(None, 0.5) == 0.5
    assert smooth(1.0, 0.0) == 0.7
