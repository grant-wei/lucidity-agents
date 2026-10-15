"""What the model knows about an industry at the end of a month, before next month's return."""
from collections import defaultdict
import math

NAMES = ["ret_1m", "ret_12m", "ret_2_12m", "mkt_rf", "smb", "hml", "rmw", "cma", "mom", "firms", "log_size", "be_me"]


class Tracker:
    def __init__(self):
        self.history = defaultdict(list)
        self.factors = []
        self.info = defaultdict(list)

    def features(self, industry):
        h = self.history[industry]
        f = self.factors[-1] if self.factors else {}
        d = self.info[industry][-1] if self.info[industry] else {}
        be = d.get("be_me")
        return [
            h[-1] if h else 0.0,
            sum(h[-12:]) if h else 0.0,
            sum(h[-12:-1]) if len(h) > 1 else 0.0,
            *[f.get(k, 0.0) for k in ("mkt_rf", "smb", "hml", "rmw", "cma", "mom")],
            math.log1p(d.get("firms", 0)),
            math.log1p(max(d.get("size", 0.0), 0.0)),
            be if be is not None else 0.0,
        ]

    def update(self, month, returns, info):
        for industry, r in returns.items():
            self.history[industry].append(r)
        self.factors.append(info["factors"])
        for industry, d in info["industries"].items():
            self.info[industry].append(d)
