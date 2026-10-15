"""What the model knows about a game before tip-off.

The eval walks the games in date order. Same-day results are applied only after every
feature for that date has been produced.
"""
from collections import defaultdict
import math

NAMES = ["home_win_pct", "away_win_pct", "elo_home_edge"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        h, a = game["home"], game["away"]
        # Express rating gap as a bounded probability-like quantity for regularization.
        gap = self.elo[h] - self.elo[a] + 65.0
        elo_edge = 1.0 / (1.0 + 10.0 ** (-gap / 400.0))
        return [self._pct(game["season"], h), self._pct(game["season"], a), elo_edge]

    def update(self, game):
        h, a = game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        expected = 1.0 / (1.0 + 10.0 ** (-(self.elo[h] - self.elo[a] + 65.0) / 400.0))
        change = 20.0 * ((1.0 if home_won else 0.0) - expected)
        self.elo[h] += change
        self.elo[a] -= change
        s = game["season"]
        for team, won in ((h, home_won), (a, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
