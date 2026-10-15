"""Predicts whether the home team wins an NBA game, from what was known before tip-off."""
import csv
from pathlib import Path

from .features import NAMES, Tracker
from .model import make_model

DATA = Path(__file__).resolve().parent.parent / "data" / "games.csv"
SPLITS = {"train": range(2001, 2013), "dev": range(2013, 2014), "heldout": range(2014, 2016)}


def load_games():
    with open(DATA, newline="", encoding="utf-8") as fh:
        out = []
        for r in csv.DictReader(fh):
            for k in ("season", "playoffs", "home_pts", "away_pts"):
                r[k] = int(r[k])
            out.append(r)
    return out


def featurize(games):
    """Each game's features, computed in date order from earlier games only."""
    tracker, rows, i = Tracker(), [], 0
    while i < len(games):
        j = i
        while j < len(games) and games[j]["date"] == games[i]["date"]:
            j += 1
        day = games[i:j]
        rows += [tracker.features(g) for g in day]
        for g in day:
            tracker.update(g)
        i = j
    return rows
