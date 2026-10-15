"""Naive Bayes model for game outcomes."""
import numpy as np
from sklearn.naive_bayes import GaussianNB


class TeamRateNaiveBayes:
    """Gaussian NB using team rates and their matchup contrast."""
    def __init__(self):
        self.model = GaussianNB(var_smoothing=0.05)

    @staticmethod
    def _transform(X):
        x = np.asarray(X, dtype=float)
        home, away = x[:, 0], x[:, 1]
        # The difference carries matchup signal; the mean retains information about
        # whether both teams are strong/weak, while keeping this a NB classifier.
        return np.column_stack((home - away, (home + away) / 2))

    def fit(self, X, y):
        self.model.fit(self._transform(X), y)
        return self

    def predict_proba(self, X):
        return self.model.predict_proba(self._transform(X))


def make_model():
    return TeamRateNaiveBayes()
