"""Ordinary least-squares risk model, with probabilities clipped to [1%, 99%]."""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LinearRegression


class ClippedLinearRegression(BaseEstimator, ClassifierMixin):
    def __init__(self):
        self.regressor = LinearRegression()

    def fit(self, X, y):
        self.regressor.fit(X, y)
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        p = np.clip(self.regressor.predict(X), 0.01, 0.99)
        return np.column_stack((1 - p, p))


def make_model():
    return ClippedLinearRegression()
