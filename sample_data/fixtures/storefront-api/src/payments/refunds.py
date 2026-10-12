"""Partial refunds: never refund more than the order total."""
from db.models import Order, Refund
from db.session import db
from .stripe_client import refund


def refund_order(order_id, cents):
    order = db.get(Order, order_id)
    done = sum(r.cents for r in order.refunds)
    if done + cents > order.total_cents:
        raise ValueError("refund exceeds order total")
    refund(order.charge_id, cents)
    db.add(Refund(order_id=order_id, cents=cents))
