"""Vendor: who sent the invoice."""
from ..text import nonblank


def vendor(text):
    rows = nonblank(text)
    return rows[0] if rows else None
