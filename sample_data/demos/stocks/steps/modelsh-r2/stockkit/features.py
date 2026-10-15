"""Leakage-safe monthly industry features."""
from collections import defaultdict
import math

NAMES = ["ret_1m", "ret_3m", "ret_6m", "ret_12m", "ret_36m", "vol_12m",
         "log_firms", "log_size", "be_me", "mkt_rf", "smb", "hml", "mom"]

class Tracker:
    def __init__(self):
        self.history = defaultdict(list)
        self.factors = []
        self.info = defaultdict(list)

    def features(self, industry):
        h = self.history[industry]
        def total(n): return sum(h[-n:]) if h else 0.0
        recent = h[-12:]
        vol = (sum((x - sum(recent)/len(recent))**2 for x in recent)/len(recent))**.5 if recent else 0.0
        d = self.info[industry][-1] if self.info[industry] else {}
        f = self.factors[-1] if self.factors else {}
        return [h[-1] if h else 0.0, total(3), total(6), total(12), total(36), vol,
                math.log1p(d.get("firms", 0)), math.log1p(max(0, d.get("size", 0))),
                d.get("be_me") or 0.0, f.get("mkt_rf", 0), f.get("smb", 0), f.get("hml", 0), f.get("mom", 0)]

    def update(self, month, returns, info):
        for industry, r in returns.items(): self.history[industry].append(r)
        self.factors.append(info.get("factors", {}))
        for industry, d in info.get("industries", {}).items(): self.info[industry].append(d)
