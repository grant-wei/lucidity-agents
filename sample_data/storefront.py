"""The sample repo the architecture map draws (storefront-api), and four older, finished sessions
that edited it. The sessions sit outside the monitor's 3-day window and have no labels, so they
change no eval; only the map reads them. Everything here is invented."""
from datetime import timedelta

SF = "/Users/sam/code/storefront-api"

RESERVATION_MODEL = '''
class Reservation(Base):
    __tablename__ = "reservations"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str]
    qty: Mapped[int]
    order_id: Mapped[int]
'''

FILES = {
    "README.md": "# storefront-api\n\nOrders, checkout, payments and stock for a small online shop.\n",
    "src/app.py": '''"""Entry point: builds the HTTP app and mounts the routes."""
from api.routes import ROUTES
from db.session import engine


def create_app():
    return {"routes": ROUTES, "engine": engine}
''',
    "src/checkout.py": '''"""Turns a cart into an order: prices it, applies discounts, holds stock, charges the card."""
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
''',
    "src/discounts.py": '''"""Discount codes and how they change a cart total."""
CODES = {"WELCOME": 10, "SPRING": 15}


def apply_discount(cart, code):
    pct = CODES.get(code.upper(), 0)
    return cart.total * (1 - pct / 100)
''',
    "src/api/__init__.py": "",
    "src/api/routes.py": '''"""HTTP routes: maps method and path to handlers."""
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
''',
    "src/api/errors.py": '''"""JSON error responses."""


def error(status, message):
    return status, {"error": message}
''',
    "src/auth/__init__.py": "",
    "src/auth/login.py": '''"""Password login and session tokens."""
from .ratelimit import allow
from .users import find_by_email
from .tokens import issue


def login(request):
    if not allow(request.ip):
        return 429, {"error": "too many attempts"}
    user = find_by_email(request.json["email"])
    if not user or not user.check(request.json["password"]):
        return 401, {"error": "bad credentials"}
    return 200, {"token": issue(user)}
''',
    "src/auth/ratelimit.py": '''"""Sliding-window limit on login attempts per IP."""
import time
from collections import defaultdict, deque

WINDOW, LIMIT = 60, 5
_hits = defaultdict(deque)


def allow(ip):
    now, q = time.time(), _hits[ip]
    while q and now - q[0] > WINDOW:
        q.popleft()
    q.append(now)
    return len(q) <= LIMIT
''',
    "src/auth/tokens.py": '''"""Signed session tokens."""
import hashlib


def issue(user):
    return hashlib.sha256(f"{user.id}".encode()).hexdigest()
''',
    "src/auth/users.py": '''"""User lookup."""
from sqlalchemy import select
from db.models import User
from db.session import db


def find_by_email(email):
    return db.scalar(select(User).where(User.email == email))
''',
    "src/payments/__init__.py": "",
    "src/payments/stripe_client.py": '''"""Thin wrapper over the Stripe API: charges and refunds."""


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
''',
    "src/payments/refunds.py": '''"""Partial refunds: never refund more than the order total."""
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
''',
    "src/inventory/__init__.py": "",
    "src/inventory/stock.py": '''"""Stock levels per SKU."""
from sqlalchemy import select
from db.models import Stock
from db.session import db


def in_stock(sku):
    row = db.scalar(select(Stock).where(Stock.sku == sku))
    return row.qty if row else 0
''',
    "src/inventory/reservations.py": '''"""Holds stock for an order until payment succeeds."""
from db.models import Reservation
from db.session import db


def hold(cart):
    for item in cart.items:
        db.add(Reservation(sku=item.sku, qty=item.qty, order_id=cart.id))


def release(cart):
    db.query(Reservation).filter_by(order_id=cart.id).delete()
''',
    "src/db/__init__.py": "",
    "src/db/models.py": '''"""Tables: users, orders, refunds, stock, reservations."""
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    total_cents: Mapped[int]


class Refund(Base):
    __tablename__ = "refunds"
    id: Mapped[int] = mapped_column(primary_key=True)
    cents: Mapped[int]


class Stock(Base):
    __tablename__ = "stock"
    sku: Mapped[str] = mapped_column(primary_key=True)
    qty: Mapped[int]
''' + RESERVATION_MODEL,
    "src/db/session.py": '''"""Database engine and session (SQLAlchemy 2)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine("sqlite:///store.db")
db = Session(engine)
''',
    "tests/test_checkout.py": "from checkout import place_order\n\n\ndef test_discount_unknown_code():\n    assert place_order\n",
    "tests/test_refunds.py": "from payments.refunds import refund_order\n\n\ndef test_cannot_refund_more_than_total():\n    assert refund_order\n",
    "tests/test_reservations.py": "from inventory.reservations import hold, release\n\n\ndef test_release_on_failed_payment():\n    assert hold and release\n",
    "tests/test_auth.py": "from auth.login import login\n\n\ndef test_rate_limited():\n    assert login\n",
    "scripts/seed_stock.py": '''"""Load starting stock from a CSV."""
from inventory.stock import in_stock
''',
}


def _lines(text):
    return text.strip("\n").splitlines()


def write_repo(fx):
    root = fx / "storefront-api"
    for rel, text in FILES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")


def sessions(ClaudeWriter, CodexWriter, now):
    out = []

    w = ClaudeWriter("f1a2b3c4-0101-4f00-9000-000000000101", SF, now - timedelta(days=5, hours=3))
    w.user("support partial refunds through stripe. an order can be refunded in parts up to its total. add tests")
    w.tick(6)
    w.call("Read", {"file_path": f"{SF}/src/payments/stripe_client.py"}, FILES["src/payments/stripe_client.py"][:400],
           text="Reading the Stripe client first.")
    w.call("Write", {"file_path": f"{SF}/src/payments/refunds.py", "content": FILES["src/payments/refunds.py"]},
           "File created successfully.", text="Adding a refunds module that tracks how much of an order is already refunded.",
           out_tokens=900, grow=4000)
    w.call("Edit", {"file_path": f"{SF}/src/payments/stripe_client.py", "old_string": "def charge(",
                    "new_string": "def refund(charge_id, cents):\n    return _post('/v1/refunds', charge=charge_id, amount=cents)\n\n\ndef charge("},
           "The file has been updated.", out_tokens=300)
    w.call("Edit", {"file_path": f"{SF}/src/api/routes.py", "old_string": "from checkout import place_order",
                    "new_string": "from checkout import place_order\nfrom payments.refunds import refund_order"},
           "The file has been updated.", text="Exposing it as POST /orders/<id>/refunds.", out_tokens=250)
    w.call("Edit", {"file_path": f"{SF}/src/api/routes.py", "old_string": "ROUTES = {",
                    "new_string": "ROUTES = {\n    ('POST', '/orders/<id>/refunds'): refund_order,"},
           "The file has been updated.", out_tokens=200)
    w.call("Write", {"file_path": f"{SF}/tests/test_refunds.py", "content": FILES["tests/test_refunds.py"]},
           "File created successfully.", out_tokens=700, grow=3000)
    w.call("Bash", {"command": "pytest -q", "description": "Run tests"}, "................................\n31 passed in 2.4s")
    w.assistant("Partial refunds are in: payments/refunds.py caps the running total at the order amount, "
                "the API has POST /orders/<id>/refunds, and 5 new tests pass (31 total).")
    out.append(w)

    w = CodexWriter("019a0b1c-0102-7000-8000-000000000102", SF, now - timedelta(days=4, hours=6))
    w.user("checkout sometimes oversells the last unit. reserve stock when the order is placed and release it if payment fails")
    w.say("I'll add a reservations table and hold stock inside checkout before charging.")
    w.call("rg -n 'def place_order' src", "src/checkout.py:9:def place_order(cart, user):")
    w.patch([("Add", f"{SF}/src/inventory/reservations.py", _lines(FILES["src/inventory/reservations.py"]), []),
             ("Update", f"{SF}/src/db/models.py", _lines(RESERVATION_MODEL), [])])
    w.patch([("Update", f"{SF}/src/checkout.py",
              ["from inventory.reservations import hold, release", "    hold(cart)", "    try:",
               "        charge(user.card, total)", "    except PaymentFailed:", "        release(cart)", "        raise"],
              ["    stock.decrement(cart)", "    charge(user.card, total)"])])
    w.patch([("Add", f"{SF}/tests/test_reservations.py", _lines(FILES["tests/test_reservations.py"]), [])])
    w.call("pytest -q", "..................................\n34 passed in 2.6s")
    w.say("Stock is now held when an order is placed and released if the charge fails. 3 new tests, 34 passing.", final=True)
    out.append(w)

    w = ClaudeWriter("f1a2b3c4-0103-4f00-9000-000000000103", SF, now - timedelta(days=3, hours=20))
    w.user("someone is brute forcing /login. add a per-ip rate limit, 5 tries per minute")
    w.tick(5)
    w.call("Read", {"file_path": f"{SF}/src/auth/login.py"}, FILES["src/auth/login.py"][:400])
    w.call("Write", {"file_path": f"{SF}/src/auth/ratelimit.py", "content": FILES["src/auth/ratelimit.py"]},
           "File created successfully.", text="A small sliding-window limiter keyed by IP.", out_tokens=600, grow=2500)
    w.call("Edit", {"file_path": f"{SF}/src/auth/login.py", "old_string": "def login(request):",
                    "new_string": "from .ratelimit import allow\n\n\ndef login(request):\n    if not allow(request.ip):\n"
                                  "        return 429, {'error': 'too many attempts'}"},
           "The file has been updated.", out_tokens=250)
    w.call("Bash", {"command": "pytest tests/test_auth.py -q", "description": "Run auth tests"}, "........\n8 passed in 0.6s")
    w.assistant("Login is limited to 5 attempts per IP per minute and returns 429 after that. Auth tests pass.")
    out.append(w)

    w = CodexWriter("019a0b1c-0104-7000-8000-000000000104", SF, now - timedelta(days=6, hours=2))
    w.user("move the db layer to sqlalchemy 2 style (select() instead of query()). keep behavior the same")
    w.say("Updating the session helper and models, then every query call site.")
    w.patch([("Update", f"{SF}/src/db/session.py", _lines(FILES["src/db/session.py"]),
              ["Session = sessionmaker(engine)", "def get(model, id):", "    return Session().query(model).get(id)"]),
             ("Update", f"{SF}/src/db/models.py", ["class Base(DeclarativeBase):", "    pass"], ["Base = declarative_base()"])])
    w.patch([("Update", f"{SF}/src/inventory/stock.py", ["    row = db.scalar(select(Stock).where(Stock.sku == sku))"],
              ["    row = db.query(Stock).filter_by(sku=sku).one()"]),
             ("Update", f"{SF}/src/auth/users.py", ["    return db.scalar(select(User).where(User.email == email))"],
              ["    return db.query(User).filter_by(email=email).first()"])])
    w.call("pytest -q", "............................\n26 passed in 2.2s")
    w.say("The db layer uses SQLAlchemy 2 select() everywhere; behavior unchanged, 26 tests pass.", final=True)
    out.append(w)
    return out
