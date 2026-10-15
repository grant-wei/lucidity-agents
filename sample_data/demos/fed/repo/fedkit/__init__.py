"""Predicts whether the Federal Reserve raises its target rate next month, from what was known this month."""
import csv
from pathlib import Path

from .features import NAMES, features
from .model import make_model

DATA = Path(__file__).resolve().parent.parent / "data" / "months.csv"
SPLITS = {"train": range(1985, 2005), "dev": range(2005, 2015), "heldout": range(2015, 2100)}   # by year


def load_months():
    """Every month, oldest first. features(months, i) may only look at months[:i + 1]."""
    with open(DATA, newline="", encoding="utf-8") as fh:
        return [{k: v if k == "month" else (int(v) if k == "hike_next" else float(v)) for k, v in r.items()}
                for r in csv.DictReader(fh)]


def split_of(month):
    year = int(month["month"][:4])
    return next(name for name, years in SPLITS.items() if year in years)
