"""Leakage-safe end-of-month features."""
from collections import defaultdict
import math

NAMES = ["ret_1m", "ret_12m", "ret_3m", "ret_6m", "mom_12m", "firms", "log_size", "be_me",
         "mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf"]


class Tracker:
    def __init__(self):
        self.history = defaultdict(list)
        self.factors = []
        self.info = defaultdict(list)

    def features(self, industry):
        h = self.history[industry]
        d = self.info[industry][-1] if self.info[industry] else {}
        f = self.factors[-1] if self.factors else {}
        returns = [h[-1] if h else 0.0, sum(h[-12:]) if h else 0.0,
                   sum(h[-3:]) if h else 0.0, sum(h[-6:]) if h else 0.0,
                   sum(h[-12:-1]) if len(h) > 1 else 0.0]
        return returns + [math.log1p(d.get("firms", 0)), math.log1p(max(0, d.get("size", 0))),
                          d.get("be_me") or 0.0] + [f.get(k, 0.0) for k in ("mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf")]

    def update(self, month, returns, info):
        for industry, r in returns.items():
            self.history[industry].append(r)
        self.factors.append(info["factors"])
        for industry, d in info["industries"].items():
            self.info[industry].append(d)
