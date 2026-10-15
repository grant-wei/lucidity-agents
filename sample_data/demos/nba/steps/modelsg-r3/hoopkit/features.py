"""Pre-game team features, updated only after all games on a date."""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "elo_diff", "home_elo", "away_elo",
         "net_rating_diff", "games_played_diff"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.margin = defaultdict(float)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        s, h, a = game["season"], game["home"], game["away"]
        he, ae = self.elo[h], self.elo[a]
        hg, ag = self.games[s, h], self.games[s, a]
        # Prior-season/sample noise is shrunk toward a neutral rating.
        hn = self.margin[s, h] / (hg + 8.)
        an = self.margin[s, a] / (ag + 8.)
        return [self._pct(s, h), self._pct(s, a), he - ae, he - 150., ae - 150., hn - an, hg - ag]

    def update(self, game):
        s, h, a = game["season"], game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        rh, ra = self.elo[h], self.elo[a]
        expected = 1. / (1. + 10. ** ((ra - rh - 65.) / 400.))
        delta = 20. * ((1. if home_won else 0.) - expected)
        self.elo[h] += delta
        self.elo[a] -= delta
        margin = game["home_pts"] - game["away_pts"]
        self.margin[s, h] += margin
        self.margin[s, a] -= margin
        for team, won in ((h, home_won), (a, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
