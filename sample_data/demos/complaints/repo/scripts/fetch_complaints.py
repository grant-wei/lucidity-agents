"""Rebuild data/ from the CFPB Consumer Complaint Database.

    pip install pyarrow
    python scripts/fetch_complaints.py path/to/train-00000-of-00003.parquet

The CFPB no longer publishes complaint narratives (its API and bulk CSV dropped the column), so this
reads a CC0 mirror of the database as it stood in February 2024: the `has-text` shard 0 of
huggingface.co/datasets/BEE-spoke-data/consumer-finance-complaints. It takes complaints received in
2023 or later, keeps narratives 300-1,500 characters long, drops near-duplicates (form letters are
common), and samples the same number per product with a fixed seed: half to data/dev, half to
data/heldout. The CFPB scrubbed personal details before publishing; they appear as XXXX."""
import json
import random
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq

PRODUCTS = {
    "credit_reporting": ("Credit reporting, credit repair services, or other personal consumer reports",
                         "Credit reporting or other personal consumer reports"),
    "debt_collection": ("Debt collection",),
    "credit_card": ("Credit card or prepaid card", "Credit card"),
    "checking_savings": ("Checking or savings account",),
    "money_transfer": ("Money transfer, virtual currency, or money service",),
    "mortgage": ("Mortgage",),
}
PER_PRODUCT = 48  # 24 dev + 24 held out
DATA = Path(__file__).resolve().parent.parent / "data"


def main(parquet):
    t = pq.read_table(parquet, columns=["Date received", "Product", "Consumer complaint narrative", "Complaint ID"])
    label_of = {name: label for label, names in PRODUCTS.items() for name in names}
    pools = {label: [] for label in PRODUCTS}
    seen = set()
    for date, product, text, cid in zip(*(t.column(c).to_pylist() for c in t.column_names)):
        label = label_of.get(product)
        if not label or date < "2023-01-01" or not text:
            continue
        text = " ".join(text.split())
        sig = re.sub(r"[^a-z]", "", text.lower())[:120]
        if 300 <= len(text) <= 1500 and sig not in seen:
            seen.add(sig)
            pools[label].append({"id": str(cid), "text": text, "product": label})
    rng = random.Random(409)
    rows = {"dev": [], "heldout": []}
    for label, pool in pools.items():
        pool.sort(key=lambda r: r["id"])
        picked = rng.sample(pool, PER_PRODUCT)
        rows["dev"] += picked[: PER_PRODUCT // 2]
        rows["heldout"] += picked[PER_PRODUCT // 2:]
        print(f"{label}: {len(pool)} usable, took {PER_PRODUCT}")
    DATA.mkdir(exist_ok=True)
    for split, items in rows.items():
        rng.shuffle(items)
        with open(DATA / f"{split}.jsonl", "w", encoding="utf-8", newline="\n") as fh:
            fh.writelines(json.dumps(r) + "\n" for r in items)


if __name__ == "__main__":
    main(sys.argv[1])
