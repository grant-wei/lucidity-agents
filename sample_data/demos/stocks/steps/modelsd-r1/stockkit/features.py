"""Point-in-time industry and market features."""
from collections import defaultdict
import math

NAMES = ["ret_1m", "ret_12m", "ret_3m", "ret_6m", "ret_36m", "factor_mkt_rf", "factor_smb", "factor_hml", "factor_rmw", "factor_cma", "factor_mom", "factor_rf", "firms", "size", "be_me"]


class Tracker:
    def __init__(self):
        self.history = defaultdict(list)
        self.factors = []
        self.info = defaultdict(list)

    def features(self, industry):
        h = self.history[industry]
        f = self.factors[-1] if self.factors else {}
        d = self.info[industry][-1] if self.info[industry] else {}
        vals = [h[-1] if h else 0., sum(h[-12:]), sum(h[-3:]), sum(h[-6:]), sum(h[-36:])]
        vals += [f.get(key, 0.) for key in ("mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf")]
        vals += [math.log1p(max(0, d.get("firms", 0))), math.log1p(max(0, d.get("size", 0))), d.get("be_me") or 0.]
        return vals

    def update(self, month, returns, info):
        for industry, r in returns.items():
            self.history[industry].append(r)
        self.factors.append(info.get("factors", {}))
        for industry, d in info.get("industries", {}).items():
            self.info[industry].append(d)
