"""Log loss, accuracy and a long-short spread for "beats the median industry next month" on one split.
Prints one JSON line.

    python evals/score.py               # train on 1971-2016, score 2017 to August 2026
    python evals/score.py --split dev   # train on 1971-2009, score 2010-2016 (tune here)

Lower log loss is better. A coin flip (always 0.5) scores 0.6931, and half the months are a coin
flip in practice: beating it by even 0.001 on held-out data is hard.
spread_pct is what you'd have made each month, on average, holding the 10 industries the model
liked most and shorting the 10 it liked least.
When Lucidity runs this for one of its agents (LUCIDITY_ROLE=agent), the held-out split is refused.
"""
import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stockkit import NAMES, SPLITS, examples, load_months, make_model  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="heldout", choices=["dev", "heldout"])
    args = ap.parse_args()
    if args.split == "heldout" and os.environ.get("LUCIDITY_ROLE") == "agent":
        # 2017-2026 is the referee's test. An agent that could see it could tune to it.
        print(json.dumps({"error": "held-out scores are only shown to the referee; tune with --split dev"}))
        sys.exit(2)
    t0 = time.time()
    months = load_months()
    rets = dict(months)
    rows = examples(months)
    fit_years = set(SPLITS["train"]) | (set(SPLITS["dev"]) if args.split == "heldout" else set())
    test_years = set(SPLITS[args.split])
    fit = [r for r in rows if int(r[0][:4]) in fit_years]
    test = [r for r in rows if int(r[0][:4]) in test_years]
    model = make_model()
    model.fit([r[2] for r in fit], [r[3] for r in fit])
    p = [min(max(float(q), 1e-6), 1 - 1e-6) for q in model.predict_proba([r[2] for r in test])[:, 1]]
    yt = [r[3] for r in test]
    n = len(yt)
    by_month = defaultdict(list)
    for q, r in zip(p, test):
        by_month[r[0]].append((q, rets[r[0]][r[1]]))
    spread = []
    for month, pr in by_month.items():
        pr.sort(key=lambda t: t[0])
        spread.append(sum(x for _, x in pr[-10:]) / 10 - sum(x for _, x in pr[:10]) / 10)
    metrics = {
        "log_loss": round(-sum(math.log(q if t else 1 - q) for q, t in zip(p, yt)) / n, 4),
        "accuracy": round(sum((q > 0.5) == bool(t) for q, t in zip(p, yt)) / n, 4),
        "spread_pct": round(sum(spread) / len(spread), 3),
    }
    print(json.dumps({"split": args.split, "rows": n, "months": len(by_month), "features": NAMES,
                      "model": type(model).__name__, "metrics": metrics, "seconds": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    main()
