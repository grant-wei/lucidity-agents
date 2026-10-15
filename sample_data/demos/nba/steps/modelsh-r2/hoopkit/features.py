"""What the model knows about a game before tip-off.

The eval walks games in date order, asking for all features on a date before
updating any results from that date. Thus every feature uses earlier games only.
"""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "elo_diff", "games_diff"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        s, home, away = game["season"], game["home"], game["away"]
        return [self._pct(s, home), self._pct(s, away),
                (self.elo[s, home] - self.elo[s, away] + 65.0) / 400.0,
                (self.games[s, home] - self.games[s, away]) / 20.0]

    def update(self, game):
        s = game["season"]
        home, away = game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        expected = 1.0 / (1.0 + 10 ** ((self.elo[s, away] - self.elo[s, home] - 65.0) / 400.0))
        delta = 20.0 * (int(home_won) - expected)
        self.elo[s, home] += delta
        self.elo[s, away] -= delta
        for team, won in ((home, home_won), (away, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
