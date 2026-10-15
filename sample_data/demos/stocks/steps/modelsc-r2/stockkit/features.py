"""Point-in-time features for industry next-month returns."""
from collections import defaultdict
import math

NAMES = ["ret_1m", "ret_12m", "ret_3m", "ret_6m", "ret_24m", "vol_12m",
         "mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf",
         "log_firms", "log_size", "be_me"]
FACTOR_NAMES = ["mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf"]

class Tracker:
    def __init__(self):
        self.history = defaultdict(list)
        self.factors = []
        self.info = defaultdict(list)

    def features(self, industry):
        h = self.history[industry]
        out = [h[-1] if h else 0., sum(h[-12:]), sum(h[-3:]), sum(h[-6:]), sum(h[-24:])]
        sample = h[-12:]
        mean = sum(sample) / len(sample) if sample else 0.
        out.append(math.sqrt(sum((x-mean)**2 for x in sample) / len(sample)) if sample else 0.)
        f = self.factors[-1] if self.factors else {}
        out.extend(f.get(k, 0.) for k in FACTOR_NAMES)
        d = self.info[industry][-1] if self.info[industry] else {}
        out.extend([math.log1p(max(0, d.get("firms") or 0)), math.log1p(max(0, d.get("size") or 0)), d.get("be_me") or 0.])
        return out

    def update(self, month, returns, info):
        for industry, r in returns.items():
            self.history[industry].append(r)
        self.factors.append(info.get("factors", {}))
        for industry, d in info.get("industries", {}).items():
            self.info[industry].append(d)
