"""What the model knows about a game before tip-off.

The eval walks games in date order. All features for a date are produced before any
results from that date are recorded, preventing same-day lookahead.
"""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "elo_diff", "elo_home_advantage"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        s, home, away = game["season"], game["home"], game["away"]
        rh, ra = self.elo[home], self.elo[away]
        return [self._pct(s, home), self._pct(s, away), (rh - ra) / 400.0, (rh - ra + 65.0) / 400.0]

    def update(self, game):
        s = game["season"]
        home, away = game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        for team, won in ((home, home_won), (away, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won
        rh, ra = self.elo[home], self.elo[away]
        expected = 1.0 / (1.0 + 10.0 ** (-(rh - ra + 65.0) / 400.0))
        actual = float(home_won)
        # Margin adjustment remains bounded and is based solely on this completed result.
        margin = abs(game["home_pts"] - game["away_pts"])
        k = 20.0 * min(1.5, (margin + 3.0) ** 0.5 / 6.0)
        change = k * (actual - expected)
        self.elo[home] += change
        self.elo[away] -= change

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
