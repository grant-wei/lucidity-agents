"""Pre-game team features, updated only after all games on a date."""
from collections import defaultdict
import math

NAMES = ["home_win_pct", "away_win_pct", "elo_diff", "home_elo", "away_elo"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        s, h, a = game["season"], game["home"], game["away"]
        he, ae = self.elo[h], self.elo[a]
        return [self._pct(s, h), self._pct(s, a), he - ae, he - 1500., ae - 1500.]

    def update(self, game):
        s, h, a = game["season"], game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        # Elo uses only the pre-game ratings; modest K factor and home-court advantage.
        rh, ra = self.elo[h], self.elo[a]
        expected = 1. / (1. + 10. ** ((ra - rh - 65.) / 400.))
        delta = 20. * ((1. if home_won else 0.) - expected)
        self.elo[h] += delta
        self.elo[a] -= delta
        for team, won in ((h, home_won), (a, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
