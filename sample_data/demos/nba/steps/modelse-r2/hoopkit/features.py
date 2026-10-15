"""Pregame team-strength features, updated only after each date's games."""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "home_games", "away_games",
         "home_margin", "away_margin", "home_prior_win_pct", "away_prior_win_pct"]

class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.margin = defaultdict(float)
        self.prior = defaultdict(lambda: 0.5)
        self.season_initialized = set()

    def features(self, game):
        s, h, a = game["season"], game["home"], game["away"]
        if s not in self.season_initialized:
            for team in {t for (season, t), n in self.games.items() if season == s - 1 and n}:
                self.prior[s, team] = self.wins[s-1, team] / self.games[s-1, team]
            self.season_initialized.add(s)
        return [self._pct(s, h), self._pct(s, a), self.games[s, h], self.games[s, a],
                self._margin(s, h), self._margin(s, a), self.prior[s, h], self.prior[s, a]]

    def update(self, game):
        s = game["season"]
        hw = game["home_pts"] > game["away_pts"]
        for team, won, diff in ((game["home"], hw, game["home_pts"]-game["away_pts"]),
                                (game["away"], not hw, game["away_pts"]-game["home_pts"])):
            self.games[s, team] += 1
            self.wins[s, team] += won
            self.margin[s, team] += diff

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else self.prior[season, team]

    def _margin(self, season, team):
        g = self.games[season, team]
        return self.margin[season, team] / g if g else 0.0
