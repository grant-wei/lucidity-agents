"""Score the extractor against the gold labels, field by field.

    python evals/score.py                  # held-out split, prints one JSON line
    python evals/score.py --split dev      # the split to tune on
    python evals/score.py --misses         # also print what it got wrong (dev only, to tune on)

Per field: a prediction is a true positive when it matches the label, a false positive when it is
wrong, and a miss when it is None. F1 is over those. The last line printed is the JSON scores."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from invoicekit import FIELDS, extract  # noqa: E402


def same(field, got, gold):
    if got is None:
        return False
    if field == "vendor":
        return got.strip().rstrip(".").casefold() == gold.strip().rstrip(".").casefold()
    if field == "total":
        try:
            return round(float(got), 2) == round(float(gold), 2)
        except ValueError:
            return False
    return str(got).strip() == gold


def score(split):
    folder = ROOT / "data" / split
    labels = json.loads((folder / "labels.json").read_text(encoding="utf-8"))
    counts = {f: {"tp": 0, "fp": 0, "fn": 0} for f in FIELDS}
    misses = []
    for doc, gold in labels.items():
        got = extract((folder / f"{doc}.txt").read_text(encoding="utf-8"))
        for f in FIELDS:
            if same(f, got.get(f), gold[f]):
                counts[f]["tp"] += 1
            else:
                counts[f]["fn"] += 1
                if got.get(f) is not None:
                    counts[f]["fp"] += 1
                misses.append((doc, f, got.get(f), gold[f]))
    out = {}
    for f, c in counts.items():
        p = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0
        r = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0
        out[f] = {"f1": round(2 * p * r / (p + r), 4) if p + r else 0.0, "precision": round(p, 4), "recall": round(r, 4)}
    return out, misses, len(labels)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="heldout", choices=["dev", "heldout"])
    ap.add_argument("--misses", action="store_true")
    a = ap.parse_args()
    metrics, misses, n = score(a.split)
    if a.misses and a.split == "dev":
        for doc, f, got, gold in misses:
            print(f"{doc}  {f:<15} got {got!r:<28} want {gold!r}")
    print(json.dumps({"split": a.split, "docs": n, "metrics": metrics}))


if __name__ == "__main__":
    main()
