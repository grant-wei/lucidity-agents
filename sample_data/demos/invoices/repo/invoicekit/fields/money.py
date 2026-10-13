"""Total and currency."""
from ..text import clean_token, find


def parse_amount(s):
    if not s:
        return None
    s = clean_token(s.replace("$", "").replace("USD", ""))
    try:
        return f"{float(s.replace(',', '')):.2f}"
    except ValueError:
        return None


def total(text):
    return parse_amount(find(text, r"total\s*:?\s*(.+)$"))


def currency(text):
    if "$" in text or "USD" in text:
        return "USD"
    return None
