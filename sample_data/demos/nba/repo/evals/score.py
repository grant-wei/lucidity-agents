"""Log loss, Brier score and accuracy for home-win predictions on one split. Prints one JSON line.

    python evals/score.py               # train on 2001-2013, score the 2014 and 2015 seasons
    python evals/score.py --split dev   # train on 2001-2012, score 2013 (tune here)

Lower log loss is better. Always guessing the home team's average win rate scores about 0.67.
FiveThirtyEight's Elo forecast scores 0.608 on the held-out seasons.
When Lucidity runs this for one of its agents (LUCIDITY_ROLE=agent), the held-out split is refused.
With LUCIDITY_EXPLAIN=1 it also reports each feature's importance: how much log loss rises when
that feature is shuffled across the scored games.
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

from hoopkit import NAMES, SPLITS, featurize, load_games, make_model  # noqa: E402


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="heldout", choices=["dev", "heldout"])
    args = ap.parse_args()
    if args.split == "heldout" and os.environ.get("LUCIDITY_ROLE") == "agent":
        # The 2014-15 seasons are the referee's test. An agent that could see them could tune to them.
        print(json.dumps({"error": "held-out scores are only shown to the referee; tune with --split dev"}))
        sys.exit(2)
    t0 = time.time()
    games = load_games()
    X = featurize(games)
    fit_seasons = set(SPLITS["train"]) | (set(SPLITS["dev"]) if args.split == "heldout" else set())
    test_seasons = set(SPLITS[args.split])
    fit = [i for i, g in enumerate(games) if g["season"] in fit_seasons]
    test = [i for i, g in enumerate(games) if g["season"] in test_seasons]
    y = [int(g["home_pts"] > g["away_pts"]) for g in games]
    model = make_model()
    model.fit([X[i] for i in fit], [y[i] for i in fit])
    p = [min(max(float(q), 1e-6), 1 - 1e-6) for q in model.predict_proba([X[i] for i in test])[:, 1]]
    yt = [y[i] for i in test]
    n = len(yt)
    metrics = {
        "log_loss": round(-sum(math.log(q if t else 1 - q) for q, t in zip(p, yt)) / n, 4),
        "brier": round(sum((q - t) ** 2 for q, t in zip(p, yt)) / n, 4),
        "accuracy": round(sum((q > 0.5) == bool(t) for q, t in zip(p, yt)) / n, 4),
    }
    out = {"split": args.split, "games": n, "features": NAMES, "model": type(model).__name__,
           "metrics": metrics, "seconds": round(time.time() - t0, 1)}
    if os.environ.get("LUCIDITY_EXPLAIN") == "1":
        out["importance"] = importance(model, [X[i] for i in test], yt)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
