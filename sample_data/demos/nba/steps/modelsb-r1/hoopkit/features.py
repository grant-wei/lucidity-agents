"""What the model knows about a game before tip-off.

The eval walks games in date order. Features are requested before each date's results
are applied, so the rolling team records and ratings never include the game being scored.
"""
from collections import defaultdict
import math

NAMES = ["home_win_pct", "away_win_pct", "elo_difference"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.rating = defaultdict(lambda: 1500.0)

    def features(self, game):
        season = game["season"]
        home, away = game["home"], game["away"]
        return [self._pct(season, home), self._pct(season, away),
                (self.rating[home] - self.rating[away]) / 400.0]

    def update(self, game):
        s = game["season"]
        home, away = game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        for team, won in ((home, home_won), (away, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won
        rh, ra = self.rating[home], self.rating[away]
        expected = 1.0 / (1.0 + 10.0 ** ((ra - rh) / 400.0))
        actual = float(home_won)
        change = 20.0 * (actual - expected)
        self.rating[home] = rh + change
        self.rating[away] = ra - change

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
