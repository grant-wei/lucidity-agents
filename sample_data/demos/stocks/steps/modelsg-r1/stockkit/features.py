"""What the model knows about an industry at the end of a month, before next month's return."""
from collections import defaultdict
import math

NAMES = ["ret_1m", "ret_12m", "ret_3m", "ret_6m", "vol_12m", "factor_mkt", "factor_smb", "factor_hml", "factor_mom", "log_firms", "log_size", "be_me"]


class Tracker:
    def __init__(self):
        self.history = defaultdict(list)
        self.factors = []
        self.info = defaultdict(list)

    def features(self, industry):
        h = self.history[industry]
        last = h[-1] if h else 0.0
        recent = h[-12:]
        vals = self.factors[-1] if self.factors else {}
        d = self.info[industry][-1] if self.info[industry] else {}
        return [last, sum(recent), sum(h[-3:]), sum(h[-6:]),
                math.sqrt(sum((x - sum(recent) / len(recent)) ** 2 for x in recent) / len(recent)) if recent else 0.0,
                vals.get("mkt_rf", 0.0), vals.get("smb", 0.0), vals.get("hml", 0.0), vals.get("mom", 0.0),
                math.log1p(d.get("firms", 0)), math.log1p(d.get("size", 0)), d.get("be_me") or 0.0]

    def update(self, month, returns, info):
        for industry, r in returns.items():
            self.history[industry].append(r)
        self.factors.append(info["factors"])
        for industry, d in info["industries"].items():
            self.info[industry].append(d)
