import pytest

from shop.cart import Cart
from shop.pricing.codes import UnknownCode


def test_code_applies_to_the_subtotal():
    c = Cart().add("tee").apply_code("SAVE10")
    assert c.discount() == 240 and c.total() == 2160


def test_discount_follows_later_cart_changes():
    c = Cart().add("mug").apply_code("SAVE10").add("tee")
    assert c.discount() == 370          # 10% of 3699, rounded half up


def test_unknown_code_is_refused():
    with pytest.raises(UnknownCode):
        Cart().add("mug").apply_code("NOPE")


def test_no_code_no_discount():
    assert Cart().add("pin").discount() == 0
