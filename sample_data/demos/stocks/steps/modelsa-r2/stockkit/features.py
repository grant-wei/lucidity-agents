"""Causal end-of-month predictors for next-month industry returns."""
from collections import defaultdict
NAMES = ["ret_1m", "ret_3m", "ret_6m", "ret_12m", "ret_36m"]
class Tracker:
    def __init__(self): self.history = defaultdict(list); self.factors = []; self.info = defaultdict(list)
    def features(self, industry):
        h = self.history[industry]
        return [h[-1] if h else 0., sum(h[-3:]), sum(h[-6:]), sum(h[-12:]), sum(h[-36:])]
    def update(self, month, returns, info):
        for industry, r in returns.items(): self.history[industry].append(r)
        self.factors.append(info["factors"])
        for industry, d in info["industries"].items(): self.info[industry].append(d)
