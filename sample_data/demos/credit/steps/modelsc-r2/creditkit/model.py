"""Tempered Gaussian Naive Bayes on permitted account-history features."""
import numpy as np
from sklearn.naive_bayes import GaussianNB


class AmountGaussianNB:
    def __init__(self, temperature=10.0):
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
        joint = self.model._joint_log_likelihood(self._transform(X))
        prior = np.log(self.model.class_prior_)
        logits = prior + (joint - prior) / self.temperature
        logits -= logits.max(axis=1, keepdims=True)
        q = np.exp(logits)
        return q / q.sum(axis=1, keepdims=True)


def make_model():
    return AmountGaussianNB()
