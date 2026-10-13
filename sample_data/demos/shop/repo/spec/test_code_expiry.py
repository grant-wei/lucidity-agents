from datetime import date

import pytest

from shop.pricing.codes import ExpiredCode, lookup


def test_valid_before_it_expires():
    assert lookup("SPRING", today=date(2026, 4, 1))["percent"] == 20


def test_valid_on_its_last_day():
    assert lookup("SPRING", today=date(2026, 4, 30))["percent"] == 20


def test_refused_after_it_expires():
    with pytest.raises(ExpiredCode):
        lookup("SPRING", today=date(2026, 5, 1))


def test_codes_without_a_date_never_expire():
    assert lookup("SAVE10", today=date(2099, 1, 1))["percent"] == 10
