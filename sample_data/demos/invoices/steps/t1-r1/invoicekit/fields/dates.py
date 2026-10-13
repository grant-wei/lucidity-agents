"""Invoice date."""
import re
from datetime import datetime

from ..text import lines

FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%d.%m.%Y", "%d %B %Y", "%B %d, %Y", "%b %d %Y", "%d %b %Y",
           "%B %d %Y"]
LABELS = [r"^invoice date\s*:?\s*(.+)$", r"^date of issue\s*:?\s*(.+)$", r"^issued\s*:?\s*(.+)$",
          r"(?:^|\s)date\s*:\s*(.+)$"]


def parse_date(s):
    """A date string -> ISO date, or None if the format isn't known."""
    if not s:
        return None
    s = re.sub(r"\s+", " ", s.strip().rstrip("."))
    for f in FORMATS:
        try:
            return datetime.strptime(s, f).date().isoformat()
        except ValueError:
            pass
    return None


def invoice_date(text):
    rows = lines(text)
    for pattern in LABELS:
        for ln in rows:
            if re.match(r"^(payment )?due", ln, re.IGNORECASE):
                continue
            m = re.search(pattern, ln, re.IGNORECASE)
            if m:
                return parse_date(m.group(1))
    return None
