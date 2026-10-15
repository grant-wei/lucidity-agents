"""Temporally valid per-industry features, recorded month by month."""
from collections import defaultdict
import math

_RET_WINDOWS = (1, 3, 6, 12)
_FACTOR_NAMES = ("mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf")
INFO_NAMES = ("firms", "size", "be_me")
NAMES = [*(f"ret_{n}m" for n in _RET_WINDOWS), *(f"factor_{n}" for n in _FACTOR_NAMES), *(f"info_{n}" for n in INFO_NAMES)]


class Tracker:
    def __init__(self):
        self.history = defaultdict(list)
        self.factors = []
        self.info = defaultdict(list)

    def features(self, industry):
        h = self.history[industry]
        ret = [sum(h[-n:]) if h else 0.0 for n in _RET_WINDOWS]
        f = self.factors[-1] if self.factors else {}
        factors = [float(f.get(n, 0.0)) for n in _FACTOR_NAMES]
        d = self.info[industry][-1] if self.info[industry] else {}
        raw = [d.get("firms") or 0, d.get("size") or 0, d.get("be_me") or 0]
        # Log transforms tame the highly skewed industry size/count variables.
        info = [math.log1p(max(0, raw[0])), math.log1p(max(0, raw[1])), float(raw[2])]
        return ret + factors + info

    def update(self, month, returns, info):
        for industry, r in returns.items():
            self.history[industry].append(r)
        self.factors.append(info["factors"])
        for industry, d in info["industries"].items():
            self.info[industry].append(d)
