"""Pregame team records and ratings, updated only after each date's games."""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "home_elo", "away_elo"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        s = game["season"]
        return [self._pct(s, game["home"]), self._pct(s, game["away"]),
                self.elo[game["home"]], self.elo[game["away"]]]

    def update(self, game):
        s = game["season"]
        home_won = game["home_pts"] > game["away_pts"]
        h, a = game["home"], game["away"]
        expected = 1.0 / (1.0 + 10 ** ((self.elo[a] - self.elo[h] - 100) / 400))
        result = float(home_won)
        delta = 20 * (result - expected)
        self.elo[h] += delta
        self.elo[a] -= delta
        for team, won in ((h, home_won), (a, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
