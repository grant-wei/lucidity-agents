"""Pre-game team form and Elo ratings, updated only after each date."""
from collections import defaultdict
import math

NAMES = ["home_win_pct", "away_win_pct", "elo_diff", "home_games", "away_games"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        s, h, a = game["season"], game["home"], game["away"]
        return [self._pct(s, h), self._pct(s, a),
                (self.elo[s, h] - self.elo[s, a]) / 400.0,
                min(self.games[s, h], 82) / 82.0, min(self.games[s, a], 82) / 82.0]

    def update(self, game):
        s = game["season"]
        h, a = game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        rh, ra = self.elo[s, h], self.elo[s, a]
        expected = 1.0 / (1.0 + 10 ** ((ra - rh - 65.0) / 400.0))
        margin = abs(game["home_pts"] - game["away_pts"])
        k = 20.0 * math.log1p(margin) / (2.2 + 0.001 * abs(rh - ra))
        result = float(home_won)
        self.elo[s, h] = rh + k * (result - expected)
        self.elo[s, a] = ra - k * (result - expected)
        for team, won in ((h, home_won), (a, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
