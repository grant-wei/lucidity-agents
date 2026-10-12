"""Secrets never reach the model. Every string built for a prompt or returned by a tool
passes through redact() first."""
import re

PATTERNS = [
    (re.compile(r"sk-(?:ant-|proj-)?[A-Za-z0-9_\-]{16,}"), "[REDACTED_KEY]"),
    (re.compile(r"\bAKIA[0-9A-Z]{12,}\b"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"\b[a-z]{2,8}_(?:live|test)_[A-Za-z0-9]{8,}\b"), "[REDACTED_KEY]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-~+/]{12,}=*"), "Bearer [REDACTED]"),
    (re.compile(r"(?i)\b([A-Z0-9_]*(?:API_KEY|SECRET|TOKEN|PASSWORD|PASSWD)[A-Z0-9_]*)\s*[=:]\s*['\"]?[^\s'\"]{6,}"),
     r"\1=[REDACTED]"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
]
KIND = ["API key", "AWS key", "payment/API live key", "GitHub token", "bearer token", "password or secret in env",
        "private key"]


def redact(text):
    if not text:
        return text
    out = str(text)
    for rx, repl in PATTERNS:
        out = rx.sub(repl, out)
    return out


def find_secrets(text):
    """Which kinds of secret appear in text (labels only, never the values)."""
    if not text:
        return []
    return sorted({KIND[i] for i, (rx, _) in enumerate(PATTERNS) if rx.search(str(text))})


def session_secrets(session):
    """Secret kinds seen anywhere in the session's events, with the event ids they were in."""
    hits = {}
    for e in session.events:
        for kind in find_secrets(e.text):
            hits.setdefault(kind, []).append(e.id)
    return [{"kind": k, "event_ids": v[:5]} for k, v in hits.items()]
