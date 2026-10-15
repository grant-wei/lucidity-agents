"""Predicts whether a credit-card customer misses next month's payment, from their account history."""
import csv
from pathlib import Path

from .features import NAMES, features
from .model import make_model

DATA = Path(__file__).resolve().parent.parent / "data" / "customers.csv"
SPLITS = {"train": (2, 3, 4), "dev": (1,), "heldout": (0,)}   # by customer id % 5: fixed, never reshuffled


def load_customers():
    with open(DATA, newline="", encoding="utf-8") as fh:
        out = []
        for r in csv.DictReader(fh):
            out.append({k: v if k in ("sex", "marriage") else int(v) for k, v in r.items()})
    return out


def split_of(customer):
    return next(name for name, ids in SPLITS.items() if customer["id"] % 5 in ids)
