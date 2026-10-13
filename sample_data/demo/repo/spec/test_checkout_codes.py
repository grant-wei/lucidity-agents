from shop.cart import Cart
from shop.checkout import checkout
from shop.pricing import tax_on


def test_receipt_shows_the_discount_and_taxes_the_discounted_amount():
    r = checkout(Cart().add("tee").apply_code("SAVE10"))
    assert r["code"] == "SAVE10" and r["discount"] == 240
    assert r["tax"] == tax_on(2160) and r["total"] == 2160 + tax_on(2160)


def test_receipt_without_a_code():
    r = checkout(Cart().add("tee"))
    assert r["code"] is None and r["discount"] == 0 and r["total"] == 2592
