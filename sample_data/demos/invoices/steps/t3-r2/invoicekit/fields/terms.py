"""Due date: written out, or worked out from payment terms like "Net 30" or "Due on receipt"."""
import re
from datetime import date, timedelta

from ..text import find
from .dates import invoice_date, parse_date

ON_RECEIPT = re.compile(r"\b(?:on|upon) receipt\b", re.IGNORECASE)


def due_date(text):
    written = parse_date(find(text, r"^(?:payment due|due date)\s*:?\s*(.+)$"))
    if written:
        return written
    terms = find(text, r"^terms\s*:?\s*(.+)$") or ""
    issued = invoice_date(text)
    if not issued:
        return None
    if ON_RECEIPT.search(terms):
        return issued
    m = re.search(r"net\s*(\d+)", terms, re.IGNORECASE)
    if m:
        return (date.fromisoformat(issued) + timedelta(days=int(m.group(1)))).isoformat()
    return None
