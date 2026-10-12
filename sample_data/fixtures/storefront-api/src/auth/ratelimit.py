"""Sliding-window limit on login attempts per IP."""
import time
from collections import defaultdict, deque

WINDOW, LIMIT = 60, 5
_hits = defaultdict(deque)


def allow(ip):
    now, q = time.time(), _hits[ip]
    while q and now - q[0] > WINDOW:
        q.popleft()
    q.append(now)
    return len(q) <= LIMIT
