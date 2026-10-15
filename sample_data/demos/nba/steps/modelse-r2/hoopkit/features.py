"""What the model knows about a game before tip-off.

The eval walks games in date order. Every feature uses games that have already happened;
results from the current date are applied only after all games that day are featurized.
"""
from collections import defaultdict
import math

NAMES = ["home_win_pct", "away_win_pct", "elo_diff"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        home, away = game["home"], game["away"]
        return [self._pct(game["season"], home), self._pct(game["season"], away),
                (self.elo[home] - self.elo[away]) / 400.0]

    def update(self, game):
        s = game["season"]
        home, away = game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        for team, won in ((home, home_won), (away, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won
        rh, ra = self.elo[home], self.elo[away]
        expected = 1.0 / (1.0 + 10.0 ** ((ra - rh) / 400.0))
        outcome = float(home_won)
        # A modest fixed update gives useful strength ratings without overreacting to margins.
        change = 20.0 * (outcome - expected)
        self.elo[home] += change
        self.elo[away] -= change

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
