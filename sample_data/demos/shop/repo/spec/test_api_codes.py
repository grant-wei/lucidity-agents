from shop.api import handle


def post(body):
    return handle({"method": "POST", "path": "/checkout", "body": body})


def test_checkout_with_a_code():
    status, body = post({"items": [{"sku": "tee"}], "code": "SAVE10"})
    assert status == 200 and body["discount"] == 240


def test_unknown_code_is_a_400():
    status, body = post({"items": [{"sku": "tee"}], "code": "NOPE"})
    assert status == 400 and body["error"] == "unknown code NOPE"


def test_expired_code_is_a_400():
    status, body = post({"items": [{"sku": "tee"}], "code": "SPRING"})
    assert status == 400 and body["error"] == "code SPRING has expired"
