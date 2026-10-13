"""Checkout: a cart in, a receipt out."""
from shop.pricing import tax_on


def checkout(cart):
    if not cart.items:
        raise ValueError("cart is empty")
    subtotal = cart.subtotal()
    tax = tax_on(subtotal)
    return {"items": dict(cart.items), "subtotal": subtotal, "tax": tax, "total": subtotal + tax}
