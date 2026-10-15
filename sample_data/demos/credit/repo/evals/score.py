"""Log loss, AUC and accuracy for "misses next month's payment" on one split. Prints one JSON line.

    python evals/score.py               # train on train + dev customers, score the held-out ones
    python evals/score.py --split dev   # train on train customers, score dev (tune here)

Lower log loss is better. Always guessing the average default rate (22%) scores about 0.528.
When Lucidity runs this for one of its agents (LUCIDITY_ROLE=agent), the held-out split is refused.
With LUCIDITY_EXPLAIN=1 it also reports each feature's importance: how much log loss rises when
that feature is shuffled across the scored customers.
"""
import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from creditkit import NAMES, features, load_customers, make_model, split_of  # noqa: E402


def std_err(xs):
    """Standard error of the mean: std(xs, ddof=1) / sqrt(n). A rough "could be luck" range."""
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1) / len(xs)) if len(xs) > 1 else 0.0


def importance(model, X, y):
    """Rise in log loss when each column is shuffled, mean of 5 fixed shuffles, biggest first."""
    def ll(rows):
        p = [min(max(float(q), 1e-6), 1 - 1e-6) for q in model.predict_proba(rows)[:, 1]]
        return -sum(math.log(q if t else 1 - q) for q, t in zip(p, y)) / len(y)

    base = ll(X)
    names = NAMES if len(NAMES) == len(X[0]) else [f"x{j}" for j in range(len(X[0]))]
    out = {}
    for j, name in enumerate(names):
        rises = []
        for seed in range(5):
            col = [r[j] for r in X]
            random.Random(seed).shuffle(col)
            rises.append(ll([list(r[:j]) + [c] + list(r[j + 1:]) for r, c in zip(X, col)]) - base)
        out[name] = round(sum(rises) / len(rises), 4)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def auc(p, y):
    pos = sorted(q for q, t in zip(p, y) if t)
    neg = sorted(q for q, t in zip(p, y) if not t)
    wins, j, k = 0.0, 0, 0
    for q in pos:   # pairs where a defaulter outranks a payer; ties count half
        while j < len(neg) and neg[j] < q:
            j += 1
        k = j
        while k < len(neg) and neg[k] == q:
            k += 1
        wins += j + (k - j) / 2
    return wins / (len(pos) * len(neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="heldout", choices=["dev", "heldout"])
    args = ap.parse_args()
    if args.split == "heldout" and os.environ.get("LUCIDITY_ROLE") == "agent":
        # The held-out customers are the referee's test. An agent that could see them could tune to them.
        print(json.dumps({"error": "held-out scores are only shown to the referee; tune with --split dev"}))
        sys.exit(2)
    t0 = time.time()
    people = load_customers()
    fit_splits = {"train"} | ({"dev"} if args.split == "heldout" else set())
    fit = [c for c in people if split_of(c) in fit_splits]
    test = [c for c in people if split_of(c) == args.split]
    model = make_model()
    model.fit([features(c) for c in fit], [c["default"] for c in fit])
    p = [min(max(float(q), 1e-6), 1 - 1e-6) for q in model.predict_proba([features(c) for c in test])[:, 1]]
    yt = [c["default"] for c in test]
    n = len(yt)
    losses = [-math.log(q if t else 1 - q) for q, t in zip(p, yt)]
    metrics = {
        "log_loss": round(-sum(math.log(q if t else 1 - q) for q, t in zip(p, yt)) / n, 4),
        "log_loss_se": round(std_err(losses), 5),
        "auc": round(auc(p, yt), 4),
        "accuracy": round(sum((q > 0.5) == bool(t) for q, t in zip(p, yt)) / n, 4),
    }
    out = {"split": args.split, "customers": n, "features": NAMES, "model": type(model).__name__,
           "metrics": metrics, "seconds": round(time.time() - t0, 1)}
    if os.environ.get("LUCIDITY_EXPLAIN") == "1":
        out["importance"] = importance(model, [features(c) for c in test], yt)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
