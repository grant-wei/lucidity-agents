"""What the model knows about an industry at the end of a month, before next month's return.

The eval walks the months in order. For each month it asks `features()` for every industry, then
calls `update()` with that month's returns. So a feature can only use months that already
happened: there's no way to see the return being predicted, or any later one.
"""
from collections import defaultdict

NAMES = ["ret_1m", "ret_12m"]


class Tracker:
    def __init__(self):
        self.history = defaultdict(list)   # industry -> monthly returns so far, in percent, oldest first

    def features(self, industry):
        """One list of numbers, in NAMES order, for an industry whose next month hasn't happened yet."""
        h = self.history[industry]
        return [h[-1] if h else 0.0, sum(h[-12:]) if h else 0.0]

    def update(self, month, returns):
        """Record a finished month: returns maps industry -> that month's return."""
        for industry, r in returns.items():
            self.history[industry].append(r)
