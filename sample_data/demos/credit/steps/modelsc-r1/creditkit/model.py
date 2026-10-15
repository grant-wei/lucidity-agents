"""Gaussian Naive Bayes on permitted account-history features."""
import numpy as np
from sklearn.naive_bayes import GaussianNB


class AmountGaussianNB:
    def __init__(self, temperature=30.0):
        self.model = GaussianNB(var_smoothing=1e-8)
        self.temperature = temperature

    @staticmethod
    def _transform(X):
        a = np.asarray(X, dtype=float).copy()
        a[:, 0] = np.log1p(np.maximum(a[:, 0], 0))
        for j in range(8, a.shape[1]):
            a[:, j] = np.sign(a[:, j]) * np.log1p(np.abs(a[:, j]))
        return a

    def fit(self, X, y):
        self.model.fit(self._transform(X), y)
        return self

    def predict_proba(self, X):
        # Likelihood tempering corrects Gaussian NB's overconfident independence assumption.
        p = np.clip(self.model.predict_proba(self._transform(X)), 1e-12, 1)
        z = np.log(p) / self.temperature
        z -= z.max(axis=1, keepdims=True)
        q = np.exp(z)
        return q / q.sum(axis=1, keepdims=True)


def make_model():
    return AmountGaussianNB()
