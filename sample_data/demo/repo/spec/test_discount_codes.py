import pytest

from shop.pricing.codes import UnknownCode, discount_on, lookup


def test_lookup_ignores_case_and_spaces():
    assert lookup(" save10 ")["percent"] == 10


def test_unknown_code():
    with pytest.raises(UnknownCode):
        lookup("NOPE")


def test_percent_discount_rounds_half_up():
    assert discount_on(1000, "SAVE10") == 100
    assert discount_on(999, "SAVE10") == 100


def test_flat_discount_never_exceeds_the_subtotal():
    assert discount_on(2000, "FLAT5") == 500
    assert discount_on(300, "FLAT5") == 300
