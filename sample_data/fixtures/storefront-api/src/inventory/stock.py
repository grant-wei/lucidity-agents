"""Stock levels per SKU."""
from sqlalchemy import select
from db.models import Stock
from db.session import db


def in_stock(sku):
    row = db.scalar(select(Stock).where(Stock.sku == sku))
    return row.qty if row else 0
