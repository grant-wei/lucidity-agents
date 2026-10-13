"""Due date: written out, or worked out from payment terms like "Net 30"."""
import re
from datetime import date, timedelta

from ..text import find
from .dates import invoice_date, parse_date


def due_date(text):
    written = parse_date(find(text, r"^(?:payment due|due date)\s*:?\s*(.+)$"))
    if written:
        return written
    terms = find(text, r"^terms\s*:?\s*(.+)$") or ""
    m = re.search(r"net (\d+)", terms, re.IGNORECASE)
    issued = invoice_date(text)
    if m and issued:
        return (date.fromisoformat(issued) + timedelta(days=int(m.group(1)))).isoformat()
    return None
