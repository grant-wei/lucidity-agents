"""A game's features may only depend on games played before it."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hoopkit import NAMES, featurize, load_games, make_model  # noqa: E402


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


def test_same_day_results_do_not_affect_each_other():
    games = load_games()
    day = games[0]["date"]
    same_day = [dict(g) for g in games if g["date"] == day]
    changed = [dict(g) for g in same_day]
    for game in changed:
        game["home_pts"], game["away_pts"] = game["away_pts"], game["home_pts"]
    assert featurize(same_day) == featurize(changed)


def test_model_probability_scoring_interface():
    games = load_games()[:200]
    X = featurize(games)
    y = [int(g["home_pts"] > g["away_pts"]) for g in games]
    model = make_model()
    model.fit(X, y)
    probabilities = model.predict_proba(X)
    assert probabilities.shape == (len(games), 2)
    assert all(0.0 <= p <= 1.0 for row in probabilities for p in row)
    assert all(abs(sum(row) - 1.0) < 1e-12 for row in probabilities)


def test_one_number_per_name():
    games = load_games()[:200]
    assert all(len(row) == len(NAMES) for row in featurize(games))
