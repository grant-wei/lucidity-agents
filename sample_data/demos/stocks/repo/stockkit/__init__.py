"""Predicts whether an industry's stocks beat the typical industry next month, from data known so far."""
import csv
from collections import defaultdict
from pathlib import Path

from .features import NAMES, Tracker
from .model import make_model

__all__ = ["NAMES", "SPLITS", "Tracker", "examples", "load_info", "load_months", "make_model"]

DATA = Path(__file__).resolve().parent.parent / "data" / "returns.csv"
FACTORS = DATA.parent / "factors.csv"
INFO = DATA.parent / "industry_info.csv"
SPLITS = {"train": range(1971, 2010), "dev": range(2010, 2017), "heldout": range(2017, 2027)}


def load_months():
    """[(month, {industry: return in percent})], oldest first."""
    by_month = defaultdict(dict)
    with open(DATA, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            by_month[r["month"]][r["industry"]] = float(r["ret"])
    return sorted(by_month.items())


def load_info():
    """{month: {"factors": {name: percent}, "industries": {industry: {"firms", "size", "be_me"}}}}.

    See scripts/prepare_factors.py for what each number is. be_me is None where it's missing.
    """
    info = defaultdict(lambda: {"factors": {}, "industries": {}})
    with open(FACTORS, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            info[r["month"]]["factors"] = {k: float(v) for k, v in r.items() if k != "month"}
    with open(INFO, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            info[r["month"]]["industries"][r["industry"]] = {
                "firms": int(r["firms"]), "size": float(r["size"]), "be_me": float(r["be_me"]) if r["be_me"] else None}
    return dict(info)


def examples(months, info=None):
    """One row per industry per month after the first: (month, industry, features, beat_median).

    Features are computed at the end of the month before, from earlier months only. The label is
    whether that industry's return this month beat the median industry's this month. info is
    load_info()'s output, read from data/ when not given.
    """
    info = load_info() if info is None else info
    tracker, out = Tracker(), []
    for k, (month, rets) in enumerate(months):
        if k:
            vals = sorted(rets.values())
            n = len(vals)
            median = (vals[(n - 1) // 2] + vals[n // 2]) / 2
            for industry, r in sorted(rets.items()):
                if r != median:
                    out.append((month, industry, tracker.features(industry), int(r > median)))
        tracker.update(month, rets, info.get(month, {"factors": {}, "industries": {}}))
    return out
