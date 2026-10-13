"""Discount codes. A code takes a percent off or a flat amount (in cents) off the subtotal."""

CODES = {
    "SAVE10": {"percent": 10},
    "FLAT5": {"cents": 500},
    "SPRING": {"percent": 20, "expires": "2026-04-30"},
}


class UnknownCode(KeyError):
    pass


def lookup(code):
    key = (code or "").strip().upper()
    if key not in CODES:
        raise UnknownCode(key)
    return {"code": key, **CODES[key]}


def discount_on(subtotal, code):
    c = lookup(code)
    if "percent" in c:
        off = int(subtotal * c["percent"] / 100 + 0.5)
    else:
        off = c["cents"]
    return min(off, subtotal)
