"""Leakage-safe, end-of-month features for next-month industry returns."""
from collections import defaultdict
import math

NAMES = ["ret_1m", "ret_12m", "ret_3m", "ret_6m", "ret_vol12", "factor_mkt", "factor_smb", "factor_hml", "factor_mom", "factor_rf", "firms", "size", "be_me"]


class Tracker:
    def __init__(self):
        self.history = defaultdict(list)
        self.factors = []
        self.info = defaultdict(list)

    def features(self, industry):
        h = self.history[industry]
        last = lambda n: h[-n:]
        f = self.factors[-1] if self.factors else {}
        d = self.info[industry][-1] if self.info[industry] else {}
        vals = [h[-1] if h else 0., sum(last(12)), sum(last(3)), sum(last(6))]
        recent = last(12)
        vals.append(math.sqrt(sum((x - sum(recent) / len(recent)) ** 2 for x in recent) / len(recent)) if recent else 0.)
        vals += [float(f.get(k, 0.) or 0.) for k in ("mkt_rf", "smb", "hml", "mom", "rf")]
        vals += [math.log1p(max(0, float(d.get("firms", 0) or 0))), math.log1p(max(0, float(d.get("size", 0) or 0))), float(d.get("be_me", 0) or 0)]
        return vals

    def update(self, month, returns, info):
        for industry, r in returns.items():
            self.history[industry].append(r)
        self.factors.append(info["factors"])
        for industry, d in info["industries"].items():
            self.info[industry].append(d)
