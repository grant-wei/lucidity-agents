"""Thin wrapper over the Stripe API: charges and refunds."""


class PaymentFailed(Exception):
    pass


def _post(path, **data):
    return {"path": path, **data}


def refund(charge_id, cents):
    return _post("/v1/refunds", charge=charge_id, amount=cents)


def charge(card, amount):
    if not card:
        raise PaymentFailed("no card")
    return _post("/v1/charges", source=card, amount=int(amount * 100))
