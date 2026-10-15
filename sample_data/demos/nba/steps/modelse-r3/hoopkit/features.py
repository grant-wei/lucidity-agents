"""What the model knows about a game before tip-off.

The eval walks games in date order. Every feature uses games that have already happened;
results from the current date are applied only after all games that day are featurized.
"""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "elo_diff", "home_net_rating", "away_net_rating"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.points_for = defaultdict(float)
        self.points_against = defaultdict(float)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        home, away, season = game["home"], game["away"], game["season"]
        return [self._pct(season, home), self._pct(season, away),
                (self.elo[home] - self.elo[away]) / 400.0,
                self._net(season, home), self._net(season, away)]

    def update(self, game):
        s = game["season"]
        home, away = game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        for team, won in ((home, home_won), (away, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won
        rh, ra = self.elo[home], self.elo[away]
        expected = 1.0 / (1.0 + 10.0 ** ((ra - rh) / 400.0))
        change = 20.0 * (float(home_won) - expected)
        self.elo[home] += change
        self.elo[away] -= change
        self.points_for[s, home] += game["home_pts"]
        self.points_against[s, home] += game["away_pts"]
        self.points_for[s, away] += game["away_pts"]
        self.points_against[s, away] += game["home_pts"]

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5

    def _net(self, season, team):
        g = self.games[season, team]
        # Shrink early-season estimates toward league average.
        return (self.points_for[season, team] - self.points_against[season, team]) / (g + 5.0)
