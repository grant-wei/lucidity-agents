"""Pre-game team form and Elo features, updated strictly after each date."""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "elo_diff"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        s = game["season"]
        h, a = self.elo[s, game["home"]], self.elo[s, game["away"]]
        return [self._pct(s, game["home"]), self._pct(s, game["away"]), (h-a)/400.0]

    def update(self, game):
        s = game["season"]
        home_won = game["home_pts"] > game["away_pts"]
        h, a = self.elo[s, game["home"]], self.elo[s, game["away"]]
        expected = 1.0 / (1.0 + 10.0 ** ((a-h)/400.0))
        delta = 20.0 * ((1.0 if home_won else 0.0) - expected)
        self.elo[s, game["home"]] += delta
        self.elo[s, game["away"]] -= delta
        for team, won in ((game["home"], home_won), (game["away"], not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
