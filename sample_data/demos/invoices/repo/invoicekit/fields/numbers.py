"""Invoice number."""
from ..text import clean_token, find


def invoice_number(text):
    raw = find(text, r"^(?:invoice no|inv #|number|invoice number)\s*:?\s*(\S+)")
    return clean_token(raw) if raw else None
