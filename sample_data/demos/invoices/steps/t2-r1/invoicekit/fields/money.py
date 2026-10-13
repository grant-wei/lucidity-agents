"""Total and currency."""
import re

from ..text import clean_token, lines

TOTAL_LABELS = r"^(?:total due|grand total|amount due|total)\b\s*:?\s*(.+)$"
SYMBOLS = [("€", "EUR"), ("EUR", "EUR"), ("£", "GBP"), ("GBP", "GBP"), ("$", "USD"), ("USD", "USD")]


def parse_amount(s):
    """"$1,234.50", "1.234,50 €", "GBP 980.00" -> "1234.50"."""
    if not s:
        return None
    s = clean_token(s)
    if re.search(r",\d{2}$", s):          # 1.234,50: comma is the decimal mark
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return f"{float(s):.2f}"
    except ValueError:
        return None


def _total_line(text):
    for ln in lines(text):
        m = re.match(TOTAL_LABELS, ln, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def total(text):
    return parse_amount(_total_line(text))


def currency(text):
    line = _total_line(text) or text
    for sym, code in SYMBOLS:
        if sym in line:
            return code
    return None
