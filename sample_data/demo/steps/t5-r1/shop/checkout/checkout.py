"""Checkout: a cart in, a receipt out. A code's discount comes off before tax."""
from shop.pricing import tax_on


def checkout(cart):
    if not cart.items:
        raise ValueError("cart is empty")
    subtotal = cart.subtotal()
    discount = cart.discount()
    tax = tax_on(subtotal - discount)
    return {"items": dict(cart.items), "subtotal": subtotal, "code": cart.code, "discount": discount,
            "tax": tax, "total": subtotal - discount + tax}
