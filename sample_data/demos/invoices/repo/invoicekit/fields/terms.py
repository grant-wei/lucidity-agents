"""Due date."""
from ..text import find
from .dates import parse_date


def due_date(text):
    return parse_date(find(text, r"^(?:payment due|due date)\s*:?\s*(.+)$"))
