"""Plain least-squares regression used as a probability predictor."""
import numpy as np
from sklearn.linear_model import LinearRegression


class ClippedLinearRegression:
    """Ordinary linear regression with outputs clipped to probability bounds."""
    def __init__(self):
        self.regression = LinearRegression()

    def fit(self, X, y):
        self.regression.fit(X, y)
        return self

    def predict_proba(self, X):
        p = np.clip(self.regression.predict(X), 0.01, 0.99)
        return np.column_stack((1.0 - p, p))


def make_model():
    return ClippedLinearRegression()
