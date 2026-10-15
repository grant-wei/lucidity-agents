"""What the model knows about a game before tip-off.

The eval walks the games in date order. For each date it asks `features()` for every game that
day, then calls `update()` with that day's results. So a feature can only use games that already
happened: there's no way to see the score of the game being predicted, or any later one.
"""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)     # (season, team) -> wins so far
        self.games = defaultdict(int)    # (season, team) -> games so far

    def features(self, game):
        """One list of numbers, in NAMES order, for a game that hasn't been played yet."""
        return [self._pct(game["season"], game["home"]), self._pct(game["season"], game["away"])]

    def update(self, game):
        """Record a finished game."""
        s = game["season"]
        home_won = game["home_pts"] > game["away_pts"]
        for team, won in ((game["home"], home_won), (game["away"], not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
