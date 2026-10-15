"""Leakage-safe rolling industry and market features."""
from collections import defaultdict
import math

NAMES = ["ret_1m", "ret_12m", "ret_3m", "ret_6m", "ret_36m", "vol_12m",
         "mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf", "log_firms", "log_size", "be_me"]


class Tracker:
    def __init__(self):
        self.history = defaultdict(list)
        self.factors = []
        self.info = defaultdict(list)

    def features(self, industry):
        h = self.history[industry]
        vals = [h[-1] if h else 0.0, sum(h[-12:]), sum(h[-3:]), sum(h[-6:]), sum(h[-36:])]
        tail = h[-12:]
        vals.append(math.sqrt(sum((x - sum(tail) / len(tail)) ** 2 for x in tail) / len(tail)) if tail else 0.0)
        f = self.factors[-1] if self.factors else {}
        vals.extend(f.get(k, 0.0) for k in ("mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf"))
        d = self.info[industry][-1] if self.info[industry] else {}
        vals.extend([math.log1p(d.get("firms", 0)), math.log1p(d.get("size", 0)), d.get("be_me") or 0.0])
        return vals

    def update(self, month, returns, info):
        for industry, r in returns.items():
            self.history[industry].append(r)
        self.factors.append(info["factors"])
        for industry, d in info["industries"].items():
            self.info[industry].append(d)
