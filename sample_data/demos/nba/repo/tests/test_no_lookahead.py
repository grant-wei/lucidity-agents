"""A game's features may only depend on games played before it."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hoopkit import NAMES, featurize, load_games  # noqa: E402


def test_features_ignore_the_future():
    games = load_games()[:3000]
    cut = 2000
    before = featurize(games)
    scrambled = [dict(g) for g in games]
    rng = random.Random(0)
    for g in scrambled[cut:]:   # change every result from game `cut` on
        g["home_pts"], g["away_pts"] = rng.randint(70, 130), rng.randint(70, 130)
    after = featurize(scrambled)
    first_day = games[cut]["date"]
    for i, g in enumerate(games):
        if g["date"] <= first_day:
            assert before[i] == after[i], f"game {g['game_id']}'s features changed when later results did"


def test_one_number_per_name():
    games = load_games()[:200]
    assert all(len(row) == len(NAMES) for row in featurize(games))
