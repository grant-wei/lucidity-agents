"""Naive Bayes model for game outcomes."""
import numpy as np
from sklearn.naive_bayes import GaussianNB


class TeamRateNaiveBayes:
    """Gaussian NB on pre-game team matchup contrasts."""
    def __init__(self):
        self.model = GaussianNB(var_smoothing=1e-9)

    @staticmethod
    def _transform(X):
        x = np.asarray(X, dtype=float)
        # Rates are noisy early in a season; the Elo estimate provides a
        # complementary, continuously updated measure of team strength.
        rate_diff = x[:, 0] - x[:, 1]
        elo = x[:, 2]
        # GaussianNB assumes independent inputs, so retain just one combined
        # strength contrast instead of counting correlated ratings twice.
        return np.column_stack((rate_diff, elo))

    def fit(self, X, y):
        self.model.fit(self._transform(X), y)
        return self

    def predict_proba(self, X):
        return self.model.predict_proba(self._transform(X))


def make_model():
    return TeamRateNaiveBayes()
