"""What the model knows about a game before tip-off.

The eval walks games in date order. All games on a date are featurized before any results
from that date are applied, so every feature uses earlier games only.
"""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "elo_home_probability"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        season = game["season"]
        home, away = self.elo[season, game["home"]], self.elo[season, game["away"]]
        return [self._pct(season, game["home"]), self._pct(season, game["away"]),
                1.0 / (1.0 + 10.0 ** ((away - home - 65.0) / 400.0))]

    def update(self, game):
        s = game["season"]
        home_won = game["home_pts"] > game["away_pts"]
        h, a = game["home"], game["away"]
        expected = 1.0 / (1.0 + 10.0 ** ((self.elo[s, a] - self.elo[s, h] - 65.0) / 400.0))
        change = 20.0 * (float(home_won) - expected)
        self.elo[s, h] += change
        self.elo[s, a] -= change
        for team, won in ((h, home_won), (a, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
