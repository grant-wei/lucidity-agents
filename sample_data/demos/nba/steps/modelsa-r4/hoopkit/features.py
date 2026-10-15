"""What the model knows about a game before tip-off.

The eval walks games by date. All features for one date are emitted before any
results from that date are recorded, preventing same-day lookahead.
"""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "elo_diff", "margin_diff", "experience_diff"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.margin_sum = defaultdict(float)
        self.ratings = defaultdict(lambda: 1500.0)

    def features(self, game):
        season = game["season"]
        home, away = game["home"], game["away"]
        return [self._pct(season, home), self._pct(season, away),
                (self.ratings[season, home] - self.ratings[season, away] + 65.0) / 400.0,
                self._margin(season, home) - self._margin(season, away),
                (self.games[season, home] - self.games[season, away]) / 20.0]

    def update(self, game):
        s = game["season"]
        home, away = game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        rh, ra = self.ratings[s, home], self.ratings[s, away]
        expected = 1.0 / (1.0 + 10.0 ** ((ra - (rh + 65.0)) / 400.0))
        delta = 20.0 * (float(home_won) - expected)
        self.ratings[s, home] += delta
        self.ratings[s, away] -= delta
        margin = game["home_pts"] - game["away_pts"]
        self.margin_sum[s, home] += margin
        self.margin_sum[s, away] -= margin
        for team, won in ((home, home_won), (away, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5

    def _margin(self, season, team):
        # Shrink noisy early-season estimates toward league average.
        g = self.games[season, team]
        return self.margin_sum[season, team] / (g + 8.0)
