"""What the model knows about a game before tip-off.

Features are updated only after all games on a date have been predicted.
"""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "home_point_diff", "away_point_diff"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.point_diff = defaultdict(float)

    def features(self, game):
        s = game["season"]
        return [self._pct(s, game["home"]), self._pct(s, game["away"]),
                self._diff(s, game["home"]), self._diff(s, game["away"])]

    def update(self, game):
        s = game["season"]
        home_won = game["home_pts"] > game["away_pts"]
        margin = game["home_pts"] - game["away_pts"]
        for team, won, diff in ((game["home"], home_won, margin),
                                (game["away"], not home_won, -margin)):
            self.games[s, team] += 1
            self.wins[s, team] += won
            self.point_diff[s, team] += diff

    def _pct(self, season, team):
        g = self.games[season, team]
        return (self.wins[season, team] + 10 * 0.5) / (g + 10)

    def _diff(self, season, team):
        g = self.games[season, team]
        return self.point_diff[season, team] / g if g else 0.0
