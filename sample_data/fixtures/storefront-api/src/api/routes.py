"""HTTP routes: maps method and path to handlers."""
from checkout import place_order
from payments.refunds import refund_order
from auth.login import login
from inventory.stock import in_stock

ROUTES = {
    ("POST", "/orders/<id>/refunds"): refund_order,
    ("POST", "/orders"): place_order,
    ("POST", "/login"): login,
    ("GET", "/stock/<sku>"): in_stock,
}
