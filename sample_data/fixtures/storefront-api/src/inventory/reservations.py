"""Holds stock for an order until payment succeeds."""
from db.models import Reservation
from db.session import db


def hold(cart):
    for item in cart.items:
        db.add(Reservation(sku=item.sku, qty=item.qty, order_id=cart.id))


def release(cart):
    db.query(Reservation).filter_by(order_id=cart.id).delete()
