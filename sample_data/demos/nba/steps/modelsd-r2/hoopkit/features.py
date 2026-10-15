"""Pregame features computed from games completed before tip-off."""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "home_elo", "away_elo"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        s, h, a = game["season"], game["home"], game["away"]
        return [self._pct(s, h), self._pct(s, a),
                (self.elo[h] - 1500.0) / 400.0, (self.elo[a] - 1500.0) / 400.0]

    def update(self, game):
        s = game["season"]
        home, away = game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        for team, won in ((home, home_won), (away, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won
        # Rating update uses only the result after the game; home court is handled by
        # the fitted logistic regression rather than baked into the ratings.
        eh = 1.0 / (1.0 + 10.0 ** ((self.elo[away] - self.elo[home]) / 400.0))
        outcome = float(home_won)
        margin = abs(game["home_pts"] - game["away_pts"])
        k = 20.0 * ((margin + 3.0) ** 0.3)
        change = k * (outcome - eh)
        self.elo[home] += change
        self.elo[away] -= change

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
