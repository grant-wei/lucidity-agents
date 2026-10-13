import pytest

from shop.api import handle
from shop.cart import Cart
from shop.catalog import UnknownProduct
from shop.checkout import checkout


def test_cart_subtotal():
    assert Cart().add("mug", 2).add("pin").subtotal() == 1299 * 2 + 499


def test_unknown_product_is_refused():
    with pytest.raises(UnknownProduct):
        Cart().add("sofa")


def test_checkout_adds_tax():
    r = checkout(Cart().add("tee"))
    assert r["subtotal"] == 2400 and r["tax"] == 192 and r["total"] == 2592


def test_api_checkout():
    status, body = handle({"method": "POST", "path": "/checkout", "body": {"items": [{"sku": "cap"}]}})
    assert status == 200 and body["total"] == 1850 + 148


def test_api_unknown_route():
    assert handle({"method": "GET", "path": "/nope"})[0] == 404
