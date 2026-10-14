"""F1 per product label and overall accuracy on one split, plus what the model calls cost.
Prints one JSON line.

    python evals/score.py                    # held-out split
    python evals/score.py --split dev --misses
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from complaintkit import LABELS, llm, route_many  # noqa: E402


def load(split):
    with open(ROOT / "data" / f"{split}.jsonl", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="heldout", choices=["dev", "heldout"])
    ap.add_argument("--misses", action="store_true", help="list every wrong label (use on dev)")
    args = ap.parse_args()
    rows = load(args.split)
    got = route_many([r["text"] for r in rows])
    metrics = {}
    for label in LABELS:
        tp = sum(1 for r, g in zip(rows, got) if g == label and r["product"] == label)
        fp = sum(1 for r, g in zip(rows, got) if g == label and r["product"] != label)
        fn = sum(1 for r, g in zip(rows, got) if g != label and r["product"] == label)
        p = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        metrics[label] = {"f1": round(2 * p * rc / (p + rc), 4) if p + rc else 0.0,
                          "precision": round(p, 4), "recall": round(rc, 4)}
    accuracy = sum(1 for r, g in zip(rows, got) if g == r["product"]) / len(rows)
    metrics["accuracy"] = round(accuracy, 4)
    out = {"split": args.split, "docs": len(rows), "metrics": metrics,
           "cost": {k: round(v, 6) for k, v in llm.usage.items()}}
    print(json.dumps(out))
    if args.misses:
        for r, g in zip(rows, got):
            if g != r["product"]:
                print(f"\n[{r['id']}] expected {r['product']}, got {g}\n  {r['text'][:300]}")


if __name__ == "__main__":
    main()
