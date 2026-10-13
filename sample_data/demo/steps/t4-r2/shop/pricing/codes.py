"""Discount codes. A code takes a percent off or a flat amount (in cents) off the subtotal."""
from datetime import date

CODES = {
    "SAVE10": {"percent": 10},
    "FLAT5": {"cents": 500},
    "SPRING": {"percent": 20, "expires": "2026-04-30"},
}


class UnknownCode(KeyError):
    pass


class ExpiredCode(ValueError):
    pass


def lookup(code, today=None):
    key = (code or "").strip().upper()
    if key not in CODES:
        raise UnknownCode(key)
    c = CODES[key]
    # a code still works on its expiry date and stops the day after
    if "expires" in c and (today or date.today()) > date.fromisoformat(c["expires"]):
        raise ExpiredCode(key)
    return {"code": key, **c}


def discount_on(subtotal, code):
    c = lookup(code)
    if "percent" in c:
        off = int(subtotal * c["percent"] / 100 + 0.5)
    else:
        off = c["cents"]
    return min(off, subtotal)
