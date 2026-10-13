"""Vendor: who sent the invoice. Labelled ("From:", "Remit to:") when the invoice says so, else the
first header line that isn't a title or the customer block."""
import re

from ..text import nonblank

LABELLED = re.compile(r"^(?:from|remit to|vendor|supplier)\s*:\s*(.+)$", re.IGNORECASE)
NOT_A_VENDOR = re.compile(r"^(?:invoice|tax invoice|bill to\b.*|\d.*)$", re.IGNORECASE)


def vendor(text):
    rows = nonblank(text)
    for ln in rows:
        m = LABELLED.match(ln)
        if m:
            return m.group(1).strip()
    for ln in rows[:4]:
        name = ln.strip("*").strip()
        if name and not NOT_A_VENDOR.match(name):
            return name
    return None
