"""Small text helpers every field parser shares."""
import re


def lines(text):
    return [ln.strip() for ln in text.splitlines()]


def nonblank(text):
    return [ln for ln in lines(text) if ln]


def find(text, pattern):
    """The first group of the first line that matches `pattern` (case-insensitive), or None."""
    for ln in lines(text):
        m = re.search(pattern, ln, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def clean_token(s):
    """Trim a value pulled from a label: surrounding spaces and stray punctuation."""
    return s.strip().strip(":#;,.").strip()
