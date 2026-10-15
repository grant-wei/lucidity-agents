"""Naive Bayes model for game outcomes."""
import numpy as np
from sklearn.naive_bayes import GaussianNB


class TeamRateNaiveBayes:
    """Gaussian NB on matchup contrasts derived from pre-game team information."""
    def __init__(self):
        self.model = GaussianNB(var_smoothing=0.02)

    @staticmethod
    def _transform(X):
        x = np.asarray(X, dtype=float)
        # Convert both raw win rates into a contrast; Elo is already a contrast.
        return np.column_stack((x[:, 0] - x[:, 1], x[:, 2]))

    def fit(self, X, y):
        self.model.fit(self._transform(X), y)
        return self

    def predict_proba(self, X):
        return self.model.predict_proba(self._transform(X))


def make_model():
    return TeamRateNaiveBayes()
