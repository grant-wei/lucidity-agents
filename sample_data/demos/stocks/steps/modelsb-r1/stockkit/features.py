"""What the model knows about an industry at the end of a month, before next month's return."""
from collections import defaultdict

NAMES = ["ret_1m", "ret_12m"]


class Tracker:
    def __init__(self):
        self.history = defaultdict(list)
        self.factors = []
        self.info = defaultdict(list)

    def features(self, industry):
        h = self.history[industry]
        return [h[-1] if h else 0.0, sum(h[-12:]) if h else 0.0]

    def update(self, month, returns, info):
        for industry, r in returns.items():
            self.history[industry].append(r)
        self.factors.append(info["factors"])
        for industry, d in info["industries"].items():
            self.info[industry].append(d)
