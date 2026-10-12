"""Turns a cart into an order: prices it, applies discounts, holds stock, charges the card."""
from discounts import apply_discount
from inventory.reservations import hold, release
from payments.stripe_client import charge, PaymentFailed
from db.models import Order


def place_order(cart, user):
    total = apply_discount(cart, cart.code)
    hold(cart)
    try:
        charge(user.card, total)
    except PaymentFailed:
        release(cart)
        raise
    return Order(user_id=user.id, total=total)
