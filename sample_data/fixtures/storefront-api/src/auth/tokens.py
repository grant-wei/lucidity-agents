"""Signed session tokens."""
import hashlib


def issue(user):
    return hashlib.sha256(f"{user.id}".encode()).hexdigest()
