from datetime import date
from habits.streak import current_streak


def test_consecutive():
    assert current_streak([date(2026, 10, 1), date(2026, 10, 2)]) == 2


def test_reset_after_gap():
    assert current_streak([date(2026, 10, 1), date(2026, 10, 3)]) == 1
