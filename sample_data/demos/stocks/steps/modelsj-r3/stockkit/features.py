"""Leakage-safe monthly industry features."""
from collections import defaultdict

FACTOR_NAMES = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF", "Mom"]
NAMES = ["ret_1m", "ret_3m", "ret_6m", "ret_12m", "ret_36m", "vol_12m", "vol_36m",
         "firms", "size", "be_me"] + ["factor_" + x for x in FACTOR_NAMES]

class Tracker:
    def __init__(self):
        self.history = defaultdict(list)
        self.factors = []
        self.info = defaultdict(list)

    def features(self, industry):
        h = self.history[industry]
        def total(n):
            return sum(h[-n:]) if h else 0.0
        def vol(n):
            x = h[-n:]
            return (sum((v - sum(x) / len(x)) ** 2 for v in x) / len(x)) ** .5 if len(x) > 1 else 0.0
        d = self.info[industry][-1] if self.info[industry] else {}
        f = self.factors[-1] if self.factors else {}
        return [h[-1] if h else 0.0, total(3), total(6), total(12), total(36), vol(12), vol(36),
                float(d.get("firms", 0)), float(d.get("size") or 0), float(d.get("be_me") or 0)] + [float(f.get(k, 0)) for k in FACTOR_NAMES]

    def update(self, month, returns, info):
        for industry, r in returns.items():
            self.history[industry].append(r)
        self.factors.append(info["factors"])
        for industry, d in info["industries"].items():
            self.info[industry].append(d)
