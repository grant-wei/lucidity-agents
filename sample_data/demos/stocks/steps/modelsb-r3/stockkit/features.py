"""Point-in-time industry and market features."""
from collections import defaultdict
import math

FACTOR_NAMES = ("mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf")
NAMES = ["ret_1m", "ret_12m"] + ["factor_" + k for k in FACTOR_NAMES] + ["firms", "size", "be_me"]


class Tracker:
    def __init__(self):
        self.history = defaultdict(list)
        self.factors = []
        self.info = defaultdict(list)

    def features(self, industry):
        h = self.history[industry]
        f = self.factors[-1] if self.factors else {}
        d = self.info[industry][-1] if self.info[industry] else {}
        size = d.get("size") or 0.0
        be = d.get("be_me")
        return ([h[-1] if h else 0.0, sum(h[-12:]) if h else 0.0]
                + [float(f.get(k, 0.0)) for k in FACTOR_NAMES]
                + [math.log1p(max(0, d.get("firms", 0))), math.log1p(max(0, size)), float(be or 0.0)])

    def update(self, month, returns, info):
        for industry, r in returns.items():
            self.history[industry].append(r)
        self.factors.append(info.get("factors", {}))
        for industry, d in info.get("industries", {}).items():
            self.info[industry].append(d)
