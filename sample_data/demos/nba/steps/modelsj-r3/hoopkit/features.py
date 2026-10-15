"""What the model knows about a game before tip-off.

All features for a date are produced before results from that date are recorded,
preventing same-day lookahead.
"""
from collections import defaultdict

NAMES = ["home_win_pct", "away_win_pct", "elo_diff", "elo_home_advantage",
         "win_pct_diff", "home_games", "away_games"]


class Tracker:
    def __init__(self):
        self.wins = defaultdict(int)
        self.games = defaultdict(int)
        self.elo = defaultdict(lambda: 1500.0)

    def features(self, game):
        s, home, away = game["season"], game["home"], game["away"]
        rh, ra = self.elo[home], self.elo[away]
        ph, pa = self._pct(s, home), self._pct(s, away)
        gh, ga = self.games[s, home], self.games[s, away]
        return [ph, pa, (rh - ra) / 400.0, (rh - ra + 65.0) / 400.0,
                ph - pa, gh / 82.0, ga / 82.0]

    def update(self, game):
        s = game["season"]
        home, away = game["home"], game["away"]
        home_won = game["home_pts"] > game["away_pts"]
        for team, won in ((home, home_won), (away, not home_won)):
            self.games[s, team] += 1
            self.wins[s, team] += won
        rh, ra = self.elo[home], self.elo[away]
        expected = 1.0 / (1.0 + 10.0 ** (-(rh - ra + 65.0) / 400.0))
        margin = abs(game["home_pts"] - game["away_pts"])
        k = 20.0 * min(1.5, (margin + 3.0) ** 0.5 / 6.0)
        change = k * (float(home_won) - expected)
        self.elo[home] += change
        self.elo[away] -= change

    def _pct(self, season, team):
        g = self.games[season, team]
        return self.wins[season, team] / g if g else 0.5
