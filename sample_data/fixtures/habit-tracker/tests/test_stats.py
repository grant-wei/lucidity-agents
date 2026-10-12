from datetime import date
from habits.stats import longest_streak


def test_empty_history():
    assert longest_streak([]) == 0


def test_longest_streak():
    days = [date(2026, 10, d) for d in (1, 2, 3, 4, 6)]
    assert longest_streak(days) == 4
