"""What the model knows about an industry at the end of a month, before next month's return.

The eval walks the months in order. For each month it asks `features()` for every industry, then
calls `update()` with that month's returns and other data. So a feature can only use months that
already happened: there's no way to see the return being predicted, or any later one.

Besides returns, update() gets each month's Fama-French factors and momentum (one number per month,
the same for every industry) and each industry's firm count, average size and book-to-market. The
starting features don't use them yet.
"""
from collections import defaultdict

NAMES = ["ret_1m", "ret_12m"]


class Tracker:
    def __init__(self):
        self.history = defaultdict(list)   # industry -> monthly returns so far, in percent, oldest first
        self.factors = []                  # one dict per month so far, oldest first: mkt_rf, smb, hml, rmw, cma, mom, rf
        self.info = defaultdict(list)      # industry -> one dict per month so far: firms, size ($M), be_me (None if missing)

    def features(self, industry):
        """One list of numbers, in NAMES order, for an industry whose next month hasn't happened yet."""
        h = self.history[industry]
        return [h[-1] if h else 0.0, sum(h[-12:]) if h else 0.0]

    def update(self, month, returns, info):
        """Record a finished month. returns maps industry -> that month's return; info is that month's
        {"factors": {...}, "industries": {industry: {...}}} from load_info()."""
        for industry, r in returns.items():
            self.history[industry].append(r)
        self.factors.append(info["factors"])
        for industry, d in info["industries"].items():
            self.info[industry].append(d)
