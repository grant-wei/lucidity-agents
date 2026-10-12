"""Discount codes and how they change a cart total."""
CODES = {"WELCOME": 10, "SPRING": 15}


def apply_discount(cart, code):
    pct = CODES.get(code.upper(), 0)
    return cart.total * (1 - pct / 100)
