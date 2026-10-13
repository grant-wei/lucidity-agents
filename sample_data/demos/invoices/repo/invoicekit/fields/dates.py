"""Invoice date."""
from datetime import datetime

from ..text import find

FORMATS = ["%Y-%m-%d", "%m/%d/%Y"]


def parse_date(s):
    """A date string -> ISO date, or None if the format isn't known."""
    if not s:
        return None
    for f in FORMATS:
        try:
            return datetime.strptime(s.strip(), f).date().isoformat()
        except ValueError:
            pass
    return None


def invoice_date(text):
    return parse_date(find(text, r"^(?:invoice date|date of issue|issued|date)\s*:?\s*(.+)$"))
