"""What the model knows about a game before tip-off.

The eval walks games in date order and updates team records and Elo ratings only after
all games on a date have been featurized.
"""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "elo_difference"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        season = game["season"]
        home, away = game["home"], game["away"]
        return [self._pct(season, home), self._pct(season, away),
                (self.elo[home] + 65.0 - self.elo[away]) / 400.0]

    def update(self, game):
        season = game["season"]
        home, away = game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        # Standard margin-adjusted Elo update, with a modest home-court advantage.
        rh, ra = self.elo[home], self.elo[away]
        expected = 1.0 / (1.0 + 10.0 ** ((ra - rh - 65.0) / 400.0))
        margin = abs(game["home_pts"] - game["away_pts"])
        multiplier = ((margin + 3.0) ** 0.8) / (7.5 + 0.006 * (rh - ra) * (1 if home_won else -1))
        change = 20.0 * multiplier * ((1.0 if home_won else 0.0) - expected)
        self.elo[home] += change
        self.elo[away] -= change
        for team, won in ((home, home_won), (away, not home_won)):
            self.games[season, team] += 1
            self.wins[season, team] += won

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
